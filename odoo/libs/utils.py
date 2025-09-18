"""Miscellaneous utility functions.

Pure Python utilities with no Odoo dependencies.
"""

from collections.abc import Mapping
from contextlib import ContextDecorator, suppress
from itertools import starmap
from types import FrameType


def discardattr(obj: object, key: str) -> None:
    """Perform a ``delattr(obj, key)`` but without crashing if ``key`` is not present.

    :param obj: Object to delete attribute from
    :param key: Attribute name to delete

    Example::

        >>> class Foo:
        ...     x = 1
        >>> f = Foo()
        >>> f.y = 2
        >>> discardattr(f, 'y')  # removes y
        >>> discardattr(f, 'z')  # does nothing, no error
    """
    with suppress(AttributeError):
        delattr(obj, key)


def is_list_of(values, type_: type) -> bool:
    """Return True if the given values is a list / tuple of the given type.

    :param values: The values to check
    :param type_: The type of the elements in the list / tuple

    Example::

        >>> is_list_of([1, 2, 3], int)
        True
        >>> is_list_of([1, 'a', 3], int)
        False
        >>> is_list_of('hello', str)
        False
    """
    return isinstance(values, (list, tuple)) and all(
        isinstance(item, type_) for item in values
    )


def has_list_types(values, types: tuple[type, ...]) -> bool:
    """Return True if the given values have the same types as the ones given, in the same order.

    :param values: The values to check
    :param types: The types of the elements in the list / tuple

    Example::

        >>> has_list_types([1, 'a'], (int, str))
        True
        >>> has_list_types([1, 2], (int, int))
        True
        >>> has_list_types([1, 2, 3], (int, int))
        False
    """
    return (
        isinstance(values, (list, tuple))
        and len(values) == len(types)
        and all(map(isinstance, values, types, strict=False))
    )


def format_frame(frame: FrameType) -> str:
    """Format a stack frame for display.

    :param frame: The frame object to format
    :returns: A formatted string like 'function_name filename:line_number'

    Example::

        >>> import sys
        >>> format_frame(sys._getframe())  # doctest: +ELLIPSIS
        '<module> ...:...'
    """
    code = frame.f_code
    return f"{code.co_name} {code.co_filename}:{frame.f_lineno}"


class _PrintfArgs:
    """Helper object to turn a named printf-style format string into a positional one."""

    __slots__ = ("mapping", "values")

    def __init__(self, mapping: Mapping):
        self.mapping: Mapping = mapping
        self.values: list = []

    def __getitem__(self, key):
        self.values.append(self.mapping[key])
        return "%s"


def named_to_positional_printf(string: str, args: Mapping) -> tuple[str, tuple]:
    """Convert a named printf-style format string with its arguments to positional format.

    :param string: A printf-style format string with named arguments (e.g., "%(name)s")
    :param args: A mapping of argument names to values
    :returns: A tuple of (positional_format_string, positional_args_tuple)

    Example::

        >>> named_to_positional_printf("Hello %(name)s, you are %(age)d", {'name': 'World', 'age': 42})
        ('Hello %s, you are %s', ('World', 42))
    """
    pargs = _PrintfArgs(args)
    return string.replace("%%", "%%%%") % pargs, tuple(pargs.values)


class replace_exceptions(ContextDecorator):
    """Hide some exceptions behind another error.

    Can be used as a function decorator or as a context manager.

    Example::

        @replace_exceptions(AccessError, by=NotFound())
        def super_secret_route(self):
            if not authenticated:
                raise AccessError("Route hidden to non logged-in users")
            ...

        def some_util():
            ...
            with replace_exceptions(ValueError, by=UserError("Invalid argument")):
                ...
            ...

    :param exceptions: the exception classes to catch and replace.
    :param by: the exception to raise instead.
    """

    def __init__(self, *exceptions: type[Exception], by: Exception | type[Exception]):
        if not exceptions:
            raise ValueError("Missing exceptions")

        wrong_exc = next(
            (exc for exc in exceptions if not issubclass(exc, Exception)), None
        )
        if wrong_exc:
            raise TypeError(f"{wrong_exc} is not an exception class.")

        self.exceptions = exceptions
        self.by = by

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, self.exceptions):
            if isinstance(self.by, type) and exc_value.args:
                # copy the message
                raise self.by(exc_value.args[0]) from exc_value
            raise self.by from exc_value
