import ConfigParser
import contextlib
import os
import StringIO


DEFAULTS = """\
[type:image/jpeg]
suffixes=jpeg jpg jpe
resize=false

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
    sites = []
    types = {}

    def parse_type(name, fields):
        sites.append((name, fields))

    def parse_site(name, fields):
        types[name] = fields

    parsers = {
        'type:': parse_type,
        'site:': parse_site,
    }
    for section in conf.sections():
        for prefix in parsers:
            if section.startswith(prefix):
                parsers[prefix](section[len(prefix):], conf.options(section))
                break
    return sites, types


class ImageProxy(object):

    def __init__(self):
        super(ImageProxy, self).__init__()

    def __call__(self, environ, start_response):
        start_response('200 Ok', [('Content-Type', 'text/plain')])
        return ["My response"]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    svr = make_server('localhost', 8080, ImageProxy())
    svr.serve_forever()
