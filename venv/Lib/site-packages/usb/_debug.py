# Copyright 2009-2017 Wander Lairson Costa
# Copyright 2009-2021 PyUSB contributors
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__author__ = 'Wander Lairson Costa'

__all__ = ['methodtrace', 'functiontrace']

import logging
import usb._interop as _interop

_enable_tracing = False

def enable_tracing(enable):
    global _enable_tracing
    _enable_tracing = enable

def _trace_function_call(logger, fname, *args, **named_args):
    logger.debug(
                # TODO: check if 'f' is a method or a free function
                fname + '(' + \
                ', '.join((str(val) for val in args)) + \
                ', '.join((name + '=' + str(val) for name, val in named_args.items())) + ')'
            )

# decorator for methods calls tracing
def methodtrace(logger):
    def decorator_logging(f):
        if not _enable_tracing:
            return f
        def do_trace(*args, **named_args):
            # this if is just a optimization to avoid unecessary string formatting
            if logging.DEBUG >= logger.getEffectiveLevel():
                fn = type(args[0]).__name__ + '.' + f.__name__
                _trace_function_call(logger, fn, *args[1:], **named_args)
            return f(*args, **named_args)
        _interop._update_wrapper(do_trace, f)
        return do_trace
    return decorator_logging

# decorator for methods calls tracing
def functiontrace(logger):
    def decorator_logging(f):
        if not _enable_tracing:
            return f
        def do_trace(*args, **named_args):
            # this if is just a optimization to avoid unecessary string formatting
            if logging.DEBUG >= logger.getEffectiveLevel():
                _trace_function_call(logger, f.__name__, *args, **named_args)
            return f(*args, **named_args)
        _interop._update_wrapper(do_trace, f)
        return do_trace
    return decorator_logging
