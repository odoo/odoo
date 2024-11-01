# Copyright (c) 2008 AG Projects
# Author: Denis Bilenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Trivial test that a single process (and single thread) can both read
and write from green sockets (when monkey patched).
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from gevent import monkey
monkey.patch_all()


import gevent.testing as greentest

try:
    from urllib import request as urllib2
    from http.server import HTTPServer
    from http.server import SimpleHTTPRequestHandler
except ImportError:
    # Python 2
    import urllib2
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler


import gevent
from gevent.testing import params

class QuietHandler(SimpleHTTPRequestHandler, object):

    def log_message(self, *args): # pylint:disable=arguments-differ
        self.server.messages += ((args,),)

class Server(HTTPServer, object):

    messages = ()
    requests_handled = 0

    def __init__(self):
        HTTPServer.__init__(self,
                            params.DEFAULT_BIND_ADDR_TUPLE,
                            QuietHandler)

    def handle_request(self):
        HTTPServer.handle_request(self)
        self.requests_handled += 1


class TestGreenness(greentest.TestCase):
    check_totalrefcount = False

    def test_urllib2(self):
        httpd = Server()
        server_greenlet = gevent.spawn(httpd.handle_request)

        port = httpd.socket.getsockname()[1]
        rsp = urllib2.urlopen('http://127.0.0.1:%s' % port)
        rsp.read()
        rsp.close()
        server_greenlet.join()
        self.assertEqual(httpd.requests_handled, 1)
        httpd.server_close()


if __name__ == '__main__':
    greentest.main()
