import cgi
import ConfigParser
import contextlib
import httplib
import logging
import os
import os.path
import StringIO

from PIL import Image


__all__ = (
    'create_application',
    'ImageProxy',
)


DEFAULTS = """\
[type:image/jpeg]
resize=true
"""

TEMPLATE = """\
<!DOCTYPE html>
<html>
    <head>
        <title>Directory listing for {0}</title>
        <style type="text/css" media="all">
        body {{
            font-family: sans-serif;
            margin: 0 auto;
            max-width: 40em;
            line-height: 1.5;
        }}
        h1 {{
            margin: 1em 0 0 0;
            padding: 0.125ex 1ex;
            font-size: 100%;
            border-bottom: 1px solid silver;
        }}
        ul {{
            margin: 0;
            padding: 0;
            list-style: none;
        }}
        li {{
            border-bottom: 1px solid silver;
        }}
        li a {{
            display: block;
            padding: 0.125ex 1ex;
        }}
        li a:hover {{
            background: #EEE;
        }}
        hr {{
            display: none;
        }}
        address {{
            text-align: right;
            padding: 0.125ex 1ex;
        }}
        </style>
    </head>
    <body>
        <h1>Directory listing for {0}</h1>
        <ul><li><a href="../">../</a></li>{1}</ul>
        <hr>
        <address>ImageProxy/0.1.0</address>
    </body>
</html>
"""


logger = logging.getLogger(__name__)


def load_config():
    return parse_config(read_config(DEFAULTS, 'IMAGEPROXY_SETTINGS'))


def read_config(defaults, env_var=None):
    conf = ConfigParser.RawConfigParser()
    with contextlib.closing(StringIO.StringIO(defaults)) as fp:
        conf.readfp(fp)
    if env_var is not None:
        config_path = os.getenv(env_var)
        if config_path is not None:
            conf.read(config_path)
    return conf


def parse_config(conf):
    sites = {}
    types = {}

    def parse_type(section, name):
        types[name] = conf.getboolean(section, 'resize')

    def parse_site(section, name):
        sites[name] = {
            'cache': conf.getboolean(section, 'cache'),
            'prefix': conf.get(section, 'prefix'),
            'root': conf.get(section, 'root'),
        }

    parsers = {
        'type:': parse_type,
        'site:': parse_site,
    }
    for section in conf.sections():
        for prefix in parsers:
            if section.startswith(prefix):
                parsers[prefix](section, section[len(prefix):])
                break
    return sites, types


def resize(src, dest, width, height):
    """
    Resize the given image and save it to the given sink. `src` and `dest`
    can be either file paths or handles.
    """
    img = Image.open(src)
    img.thumbnail((width, height), Image.ANTIALIAS)
    img.save(dest, 'JPEG', quality=90, optimize=True, progressive=True)


def is_subpath(base, path, sep=os.path.sep):
    """
    Check if the given path is a proper subpath of a base path.
    """
    if path.startswith(base):
        trailing = base[len(base):]
        return trailing == '' or trailing[0] == sep
    return False


def real_join(*args):
    """
    """
    return os.path.realpath(os.path.join(*args))


class HTTPError(Exception):
    """
    Application wants to respond with the given HTTP status code.
    """

    def __init__(self, code, message=None):
        if message is None:
            message = httplib.responses[code]
        super(HTTPError, self).__init__(message)
        self.code = code


def make_status_line(code):
    """
    """
    return '{0} {1}'.format(code, httplib.responses[code])


class ImageProxy(object):

    def __init__(self, sites, types):
        super(ImageProxy, self).__init__()
        self.sites = sites
        self.types = types

    def get_site_details(self, site):
        for fuzzy, details in self.sites.iteritems():
            if site.endswith(fuzzy):
                leading = site[:-len(fuzzy)]
                if leading == '' or leading[-1] == '.':
                    return details
        return None

    def list_dir(self, url_path, disc_path):
        entries = []
        for entry in sorted(os.listdir(disc_path), key=lambda v: v.lower()):
            if os.path.isdir(os.path.join(disc_path, entry)):
                entry += '/'
            entries.append(
                '<li><a href="{0}">{0}</a></li>'.format(
                    cgi.escape(entry)))
        return TEMPLATE.format(cgi.escape(url_path), ''.join(entries))

    def handle(self, environ):
        if environ['REQUEST_METHOD'] not in ('GET', 'HEAD'):
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)
        site = self.get_site_details(environ['REMOTE_HOST'])
        if site is None:
            raise HTTPError(httplib.FORBIDDEN, 'Host not allowed')
        if not is_subpath(site['prefix'], environ['PATH_INFO'], sep='/'):
            raise HTTPError(httplib.FORBIDDEN, 'Bad prefix')
        path = real_join(site['root'],
                         environ['PATH_INFO'][(len(site['prefix']) + 1):])
        if not is_subpath(site['root'], path):
            raise HTTPError(httplib.BAD_REQUEST, 'Bad path')
        if not os.path.exists(path):
            raise HTTPError(httplib.NOT_FOUND)
        if os.path.isdir(path):
            return (httplib.OK,
                    [('Content-Type', 'text/html; charset=utf-8')],
                    [self.list_dir(environ['PATH_INFO'], path)])

        return (httplib.OK,
                [('Content-Type', 'text/plain')],
                [path, ':', repr(site)])

    def __call__(self, environ, start_response):
        try:
            code, headers, result = self.handle(environ)
            start_response(make_status_line(code), headers)
            return result
        except HTTPError as exc:
            start_response(
                make_status_line(exc.code),
                [('Content-Type', 'text/plain')])
            return [exc.message]


def create_application():
    sites, types = load_config()
    return ImageProxy(sites, types)


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    svr = make_server('localhost', 8080, create_application())
    svr.serve_forever()
