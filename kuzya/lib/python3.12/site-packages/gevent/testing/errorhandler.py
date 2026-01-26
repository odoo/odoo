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
from __future__ import print_function
from functools import wraps


def wrap_error_fatal(method):
    from gevent._hub_local import get_hub_class
    system_error = get_hub_class().SYSTEM_ERROR

    @wraps(method)
    def fatal_error_wrapper(self, *args, **kwargs):
        # XXX should also be able to do gevent.SYSTEM_ERROR = object
        # which is a global default to all hubs
        get_hub_class().SYSTEM_ERROR = object
        try:
            return method(self, *args, **kwargs)
        finally:
            get_hub_class().SYSTEM_ERROR = system_error
    return fatal_error_wrapper


def wrap_restore_handle_error(method):
    from gevent._hub_local import get_hub_if_exists
    from gevent import getcurrent

    @wraps(method)
    def restore_fatal_error_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        finally:
            # Remove any customized handle_error, if set on the
            # instance.
            try:
                del get_hub_if_exists().handle_error
            except AttributeError:
                pass
        if self.peek_error()[0] is not None:
            getcurrent().throw(*self.peek_error()[1:])
    return restore_fatal_error_wrapper
