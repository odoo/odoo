# Copyright (c) 2008-2009 AG Projects
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

import gevent.testing as greentest
from gevent.testing import support
from gevent.testing import sysinfo

from gevent.socket import socket, error
from gevent.exceptions import LoopExit


class TestSocketErrors(greentest.TestCase):

    __timeout__ = 5

    def test_connection_refused(self):
        port = support.find_unused_port()
        with socket() as s:
            try:
                with self.assertRaises(error) as exc:
                    s.connect((greentest.DEFAULT_CONNECT_HOST, port))
            except LoopExit:
                return
        ex = exc.exception
        self.assertIn(ex.args[0], sysinfo.CONN_REFUSED_ERRORS, ex)
        self.assertIn('refused', str(ex).lower())


if __name__ == '__main__':
    greentest.main()
