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

from functools import wraps

from gevent.hub import _get_hub

from .hub import QuietHub

from .patched_tests_setup import get_switch_expected

def wrap_switch_count_check(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        initial_switch_count = getattr(_get_hub(), 'switch_count', None)
        self.switch_expected = getattr(self, 'switch_expected', True)
        if initial_switch_count is not None:
            fullname = getattr(self, 'fullname', None)
            if self.switch_expected == 'default' and fullname:
                self.switch_expected = get_switch_expected(fullname)
        result = method(self, *args, **kwargs)
        if initial_switch_count is not None and self.switch_expected is not None:
            switch_count = _get_hub().switch_count - initial_switch_count
            if self.switch_expected is True:
                assert switch_count >= 0
                if not switch_count:
                    raise AssertionError('%s did not switch' % fullname)
            elif self.switch_expected is False:
                if switch_count:
                    raise AssertionError('%s switched but not expected to' % fullname)
            else:
                raise AssertionError('Invalid value for switch_expected: %r' % (self.switch_expected, ))
        return result
    return wrapper




class CountingHub(QuietHub):

    switch_count = 0

    def switch(self, *args):
        # pylint:disable=arguments-differ
        self.switch_count += 1
        return QuietHub.switch(self, *args)
