#!/usr/bin/env python
"""
A small WSGI app that does automatic JPEG image resizing.
"""

# Copyright (c) Keith Gaughan, 2013
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ConfigParser
import contextlib
import httplib
import logging
import mimetypes
import os
import os.path
try:
    import cStringIO as stringio
except ImportError:
    import StringIO as stringio
import urlparse
from xml.sax.saxutils import escape

from PIL import Image
import pkg_resources


__all__ = (
    'create_application',
    'ImageProxy',
)

# pylint: disable-msg=E1103
__version__ = pkg_resources.get_distribution('imageproxy').version


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
        <address>ImageProxy/{2}</address>
    </body>
</html>
"""

FORBIDDEN_TEMPLATE = """\
<!DOCTYPE html>
<html>
    <head>
        <title>Access forbidden to {0}</title>
    </head>
    <body>
        <h1>Access forbidden to {0}</h1>
        <address>ImageProxy/{1}</address>
    </body>
</html>
"""

BLOCK_SIZE = 8196


logger = logging.getLogger(__name__)


def load_config(config_file=None):
    """
    Load the config from the available sources.
    """
    return parse_config(read_config(DEFAULTS,
                                    'IMAGEPROXY_SETTINGS',
                                    config_file))


def read_config(defaults, env_var=None, config_file=None):
    """
    Combine the three possible configuration sources.
    """
    conf = ConfigParser.RawConfigParser()
    with contextlib.closing(stringio.StringIO(defaults)) as fp:
        conf.readfp(fp)
    config_files = []
    if env_var is not None and env_var in os.environ:
        config_files.append(os.getenv(env_var))
    if config_file is not None:
        config_files.append(config_file)
    conf.read(config_files)
    return conf


def parse_config(conf):
    """
    Parse the configuration out from the configuration object so as it's in
    a usable form.
    """
    sites = {}
    types = {}

    def parse_type(section, name):
        """
        Parse settings for a 'type' section.
        """
        types[name] = conf.getboolean(section, 'resize')

    def parse_site(section, name):
        """
        Parse setting for a 'site' section.
        """
        sites[name] = {
            'cache': conf.getboolean(section, 'cache'),
            'prefix': conf.get(section, 'prefix').rstrip('/'),
            'root': conf.get(section, 'root').rstrip('/'),
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

    # Figure out the corresponding other dimension.
    src_width, src_height = img.size
    if height is None:
        width = min(src_width, width)
        height = int(float(src_height) * width / src_width)
    elif width is None:
        height = min(src_height, height)
        width = int(float(src_width) * height / src_height)

    # Only resize if smaller.
    if width < src_width and height < src_height:
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
    Join and normalise a set of path fragments.
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

    def headers(self):
        """
        Additional headers to be sent.
        """
        return []


class MethodNotAllowed(HTTPError):
    """
    Method not allowed.
    """

    def __init__(self, allowed=(), message=None):
        super(MethodNotAllowed, self).__init__(httplib.METHOD_NOT_ALLOWED,
                                               message)
        self.allowed = allowed

    def headers(self):
        return [('Allow', ', '.join(self.allowed))]


def make_status_line(code):
    """
    Create a HTTP status line.
    """
    return '{0} {1}'.format(code, httplib.responses[code])


def list_dir(url_path, disc_path):
    """
    Generate a directory listing.
    """
    entries = []
    for entry in sorted(os.listdir(disc_path), key=lambda v: v.lower()):
        if os.path.isdir(os.path.join(disc_path, entry)):
            entry += '/'
        entries.append(
            '<li><a href="{0}">{0}</a></li>'.format(
                escape(entry)))
    return TEMPLATE.format(escape(url_path),
                           ''.join(entries),
                           __version__)


def list_dir_app(url_path, disc_path):
    """
    List the contents of the given directory.
    """
    return (httplib.OK,
            [('Content-Type', 'text/html; charset=utf-8')],
            [list_dir(url_path, disc_path)])


def forbidden_dir_app(url_path, disc_path):
    """
    Forbid listing the given directory.
    """
    return (httplib.FORBIDDEN,
            [('Content-Type', 'text/html; charset=utf-8')],
            [FORBIDDEN_TEMPLATE.format(escape(url_path),
                                       __version__)])


def send_named_file(environ, path):
    """
    Send the given file.
    """
    return send_file(environ, open(path, 'r'))


def resize_and_send_file(environ, path, width, height):
    """
    Resize the given image file and send it.
    """
    fh = stringio.StringIO()
    resize(path, fh, width, height)
    fh.seek(0)
    return send_file(environ, fh)


def send_file(environ, fh):
    """
    Send a file.
    """
    if 'wsgi.file_wrapper' in environ:
        return environ['wsgi.file_wrapper'](fh, BLOCK_SIZE)
    return iter(lambda: fh.read(BLOCK_SIZE), '')


def get(parameters, key, default=None, cast=str):
    """
    Get the given query string parameter.
    """
    try:
        return cast(parameters[key][0]) if key in parameters else default
    except TypeError:
        return default


def split_host(host, default_port):
    """
    Extract the hostname and port from a string.
    """
    if host[:1] == '[':
        # IPv6
        parts = host[1:].split(']', 1)
        if len(parts[1]) > 1:
            return (parts[0], parts[1].lstrip(':'))
        return (parts[0], default_port)
    else:
        # IPv4 or hostname.
        parts = host.split(':', 1)
        if len(parts) == 2:
            return tuple(parts)
        return (host, default_port)


class ImageProxy(object):
    """
    The WSGI application itself.
    """

    def __init__(self, sites, types):
        super(ImageProxy, self).__init__()
        self.sites = sites
        self.types = types

    def get_site_details(self, site):
        """
        Get the details for the given site.
        """
        for fuzzy, details in self.sites.iteritems():
            if site.endswith(fuzzy):
                leading = site[:-len(fuzzy)]
                if leading == '' or leading[-1] == '.':
                    return details
        return None

    def is_resizable(self, mimetype):
        """
        Can this mimetype be resized.
        """
        return mimetype in self.types and self.types[mimetype]

    def handle(self, environ):
        """
        Process the request.
        """
        if environ['REQUEST_METHOD'] not in ('GET', 'HEAD'):
            raise MethodNotAllowed(allowed=('GET', 'HEAD'))
        vhost, _ = split_host(environ['HTTP_HOST'], 80)
        site = self.get_site_details(vhost)
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
            return list_dir_app(environ['PATH_INFO'], path)

        mimetype, _ = mimetypes.guess_type(path)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        parameters = urlparse.parse_qs(environ.get('QUERY_STRING', ''))
        width = get(parameters, 'w', cast=int)
        height = get(parameters, 'h', cast=int)

        if not self.is_resizable(mimetype) and \
                (width is not None or height is not None):
            raise HTTPError(httplib.BAD_REQUEST, 'Resizing not allowed!')

        if not self.is_resizable(mimetype) or \
                (width is None and height is None):
            return (httplib.OK,
                    [('Content-Type', mimetype),
                     ('Content-Length', str(os.path.getsize(path)))],
                    send_named_file(environ, path))

        return (httplib.OK,
                [('Content-Type', mimetype)],
                resize_and_send_file(environ, path, width, height))

    def __call__(self, environ, start_response):
        try:
            code, headers, result = self.handle(environ)
            start_response(make_status_line(code), headers)
            return result
        except HTTPError as exc:
            start_response(
                make_status_line(exc.code),
                [('Content-Type', 'text/plain')] + exc.headers())
            return [exc.message]


# pylint: disable-msg=W0613
def create_application(global_config=None, **local_conf):
    """
    Create a configured instance of the WSGI application.
    """
    sites, types = load_config(local_conf.get('config'))
    return ImageProxy(sites, types)


def main():
    """
    Run the WSGI application using :mod:`wsgiref`.
    """
    from wsgiref.simple_server import make_server
    svr = make_server('localhost', 8080, create_application())
    svr.serve_forever()


if __name__ == '__main__':
    main()
