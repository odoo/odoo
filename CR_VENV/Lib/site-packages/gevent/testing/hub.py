# Copyright (c) 2018 gevent community
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
from __future__ import absolute_import, print_function, division

from contextlib import contextmanager
from gevent.hub import Hub

from .exception import ExpectedException

class QuietHub(Hub):
    _resolver = None
    _threadpool = None

    EXPECTED_TEST_ERROR = (ExpectedException,)
    IGNORE_EXPECTED_TEST_ERROR = False

    @contextmanager
    def ignoring_expected_test_error(self):
        """
        Code in the body of this context manager will ignore
        ``EXPECTED_TEST_ERROR`` objects reported to ``handle_error``;
        they will not get a chance to go to the hub's parent.

        This completely changes the semantics of normal error handling
        by avoiding some switches (to the main greenlet, and eventually
        once a callback is processed, back to the hub). This should be used
        in narrow ways for test compatibility for tests that assume
        ``ExpectedException`` objects behave this way.
        """
        old = self.IGNORE_EXPECTED_TEST_ERROR
        self.IGNORE_EXPECTED_TEST_ERROR = True
        try:
            yield
        finally:
            self.IGNORE_EXPECTED_TEST_ERROR = old

    def handle_error(self, context, type, value, tb):
        type, value, tb = self._normalize_exception(type, value, tb)
        # If we check that the ``type`` is a subclass of ``EXPECTED_TEST_ERROR``,
        # and return, we completely change the semantics: We avoid raising
        # this error in the main greenlet, which cuts out several switches.
        # Overall, not good.

        if self.IGNORE_EXPECTED_TEST_ERROR and issubclass(type, self.EXPECTED_TEST_ERROR):
            # Don't pass these up; avoid switches
            return
        return Hub.handle_error(self, context, type, value, tb)

    def print_exception(self, context, t, v, tb):
        t, v, tb = self._normalize_exception(t, v, tb)
        if issubclass(t, self.EXPECTED_TEST_ERROR):
            # see handle_error
            return
        return Hub.print_exception(self, context, t, v, tb)
