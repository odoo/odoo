# Copyright (C) 2009-2014 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

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
