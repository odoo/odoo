# echo.py: Tracing function calls using Python decorators.
#
# Written by Thomas Guest <tag@wordaligned.org>
# Please see http://wordaligned.org/articles/echo
#
# Place into the public domain.

"""Echo calls made to functions in a module.

"Echoing" a function call means printing out the name of the function
and the values of its arguments before making the call (which is more
commonly referred to as "tracing", but Python already has a trace module).

Alternatively, echo.echo can be used to decorate functions. Calls to the
decorated function will be echoed.

Example:
-------

    @echo.echo
    def my_function(args):
        pass

"""

from __future__ import annotations

import functools
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable


def format_arg_value(arg_val: tuple[str, tuple[Any, ...]]) -> str:
    """Return a string representing a (name, value) pair."""
    arg, val = arg_val
    return f"{arg}={val!r}"


def echo(fn: Callable, write: Callable[[str], int | None] = sys.stdout.write) -> Callable:
    """Echo calls to a function.

    Returns a decorated version of the input function which "echoes" calls
    made to it by writing out the function's name and the arguments it was
    called with.
    """
    # Unpack function's arg count, arg names, arg defaults
    code = fn.__code__
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]
    fn_defaults: tuple[Any] = fn.__defaults__ or ()
    argdefs = dict(list(zip(argnames[-len(fn_defaults) :], fn_defaults)))

    @functools.wraps(fn)
    def wrapped(*v: Any, **k: Any) -> Callable:
        # Collect function arguments by chaining together positional,
        # defaulted, extra positional and keyword arguments.
        positional = list(map(format_arg_value, list(zip(argnames, v))))
        defaulted = [format_arg_value((a, argdefs[a])) for a in argnames[len(v) :] if a not in k]
        nameless = list(map(repr, v[argcount:]))
        keyword = list(map(format_arg_value, list(k.items())))
        args = positional + defaulted + nameless + keyword
        write(f"{fn.__name__}({', '.join(args)})\n")
        return fn(*v, **k)

    return wrapped
