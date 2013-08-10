import ConfigParser
import os
import StringIO


DEFAULTS = """\
[type:image/jpeg]
suffixes=jpeg jpg jpe
resize=false

[type:image/png]
suffixes=.png
resize=false

[type:image/gif]
suffixes=gif
resize=false
"""


def read_config(defaults, env_var):
    conf = ConfigParser.RawConfigParser()
    with StringIO.StringIO(defaults) as fp:
        conf.readfp(fp)
    config_path = os.getenv(env_var)
    if config_path is not None:
        conf.read(config_path)
    return conf


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
