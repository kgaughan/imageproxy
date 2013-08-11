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

    def handle(self, environ):
        if environ['REQUEST_METHOD'] not in ('GET', 'HEAD'):
            raise HTTPError(httplib.METHOD_NOT_ALLOWED)
        site = self.get_site_details(environ['REMOTE_HOST'])
        if site is None:
            raise HTTPError(httplib.FORBIDDEN, 'Host not allowed')
        if not is_subpath(site['prefix'], environ['PATH_INFO']):
            raise HTTPError(httplib.FORBIDDEN, 'Bad prefix')
        path = real_join(site['root'], environ['PATH_INFO'][1:])
        if not is_subpath(site['root'], path):
            raise HTTPError(httplib.BAD_REQUEST, 'Bad path')
        return []

    def __call__(self, environ, start_response):
        try:
            return self.handle(environ)
        except HTTPError as exc:
            start_response(
                '{0} {1}'.format(exc.code, httplib.responses[exc.code]),
                [('Content-Type', 'text/plain')])
            return [exc.message]


def create_application():
    sites, types = load_config()
    return ImageProxy(sites, types)


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    svr = make_server('localhost', 8080, create_application())
    svr.serve_forever()
