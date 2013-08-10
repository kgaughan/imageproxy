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
