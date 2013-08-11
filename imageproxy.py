import ConfigParser
import contextlib
import os
import StringIO

from PIL import Image


__all__ = (
    'create_application',
    'ImageProxy',
)


DEFAULTS = """\
[type:image/jpeg]
suffixes=jpeg jpg jpe
resize=true

[type:image/png]
suffixes=png
resize=false

[type:image/gif]
suffixes=gif
resize=false
"""


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
        values = {
            'resize': conf.getboolean(section, 'resize'),
            'mimetype': name,
        }
        for suffix in conf.get(section, 'suffixes').split(' '):
            if suffix != '':
                types[suffix] = values

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
    Resize the given image and save it at the given path.
    """
    img = Image.open(src)
    img.thumbnail((width, height), Image.ANTIALIAS)
    img.save(dest, 'JPEG', quality=90, optimize=True, progressive=True)


class ImageProxy(object):

    def __init__(self, sites, types):
        super(ImageProxy, self).__init__()
        self.sites = sites
        self.types = types

    def __call__(self, environ, start_response):
        start_response('200 Ok', [('Content-Type', 'text/plain')])
        return ["My response"]


def create_application():
    sites, types = load_config()
    return ImageProxy(sites, types)


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    svr = make_server('localhost', 8080, create_application())
    svr.serve_forever()
