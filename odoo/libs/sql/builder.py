from __future__ import annotations

import re
import typing
import warnings
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from psycopg import sql as _sql

from odoo.libs.utils import named_to_positional_printf

if TYPE_CHECKING:
    from odoo.db import Cursor
    from odoo.fields import Field
else:
    Field = typing.Any
    Cursor = typing.Any
__all__ = ["SQL"]


IDENT_RE = re.compile(r"^[a-z0-9_][a-z0-9_$\-]*\Z", re.IGNORECASE)

_PRINTF_DIRECTIVE_RE = re.compile(r"%(.)", re.DOTALL)


class SQL:
    __slots__ = ("__code", "__params", "__to_flush")

    __code: str
    __params: tuple
    __to_flush: tuple[Field, ...]

    def __init__(
        self,
        code: str | SQL = "",
        /,
        *args: object,
        to_flush: Field | Iterable[Field] | None = None,
        **kwargs: object,
    ) -> None:
        if isinstance(code, SQL):
            self.__adopt(code, args, kwargs, to_flush)
            return
        if code == "%s" and len(args) == 1 and isinstance(args[0], SQL):
            self.__adopt(args[0], (), kwargs, to_flush)
            return

        if args and kwargs:
            msg = "SQL() takes either positional arguments, or named arguments"
            raise TypeError(msg)

        if kwargs:
            code, args = named_to_positional_printf(code, kwargs)
        elif not args:
            if "%" in code:
                code % ()
            self.__code = code
            self.__params = ()
            self.__to_flush = self.__normalize_to_flush(to_flush)
            return

        code_list: list[str] = []
        params_list: list = []
        to_flush_list: list = []
        for arg in args:
            if isinstance(arg, SQL):
                code_list.append(arg.__code)
                params_list.extend(arg.__params)
                to_flush_list.extend(arg.__to_flush)
            elif isinstance(arg, tuple):
                if arg:
                    element_codes = []
                    for element in arg:
                        if isinstance(element, SQL):
                            element_codes.append(element.__code)
                            params_list.extend(element.__params)
                            to_flush_list.extend(element.__to_flush)
                        else:
                            element_codes.append("%s")
                            params_list.append(element)
                    code_list.append("(%s)" % ", ".join(element_codes))
                else:
                    code_list.append("(NULL)")
            else:
                code_list.append("%s")
                params_list.append(arg)
        to_flush_list.extend(self.__normalize_to_flush(to_flush))

        self.__code = code.replace("%%", "%%%%") % tuple(code_list)
        self.__params = tuple(params_list)
        self.__to_flush = tuple(to_flush_list)

    def __adopt(
        self,
        source: SQL,
        args: tuple,
        kwargs: dict,
        to_flush: Field | Iterable[Field] | None,
    ) -> None:
        if args or kwargs:
            msg = "SQL() unexpected arguments when code has type SQL"
            raise TypeError(msg)
        self.__code = source.__code
        self.__params = source.__params
        if to_flush is None:
            self.__to_flush = source.__to_flush
        else:
            self.__to_flush = self.__normalize_to_flush(to_flush)

    @staticmethod
    def __normalize_to_flush(
        to_flush: Field | Iterable[Field] | None,
    ) -> tuple[Field, ...]:
        if to_flush is None:
            return ()
        if isinstance(to_flush, Iterable) and not isinstance(to_flush, (str, bytes)):
            return tuple(to_flush)
        return (to_flush,)

    @property
    def code(self) -> str:
        return self.__code

    @property
    def params(self) -> tuple:
        return self.__params

    @property
    def to_flush(self) -> Iterable[Field]:
        return self.__to_flush

    def render(self) -> str:
        if not self.__params:
            return self.__code
        inlined = self.__code % tuple(str(_sql.quote(v)) for v in self.__params)
        return inlined.replace("%", "%%")

    def inlined(self, cr: Cursor) -> SQL:
        if not self.__params:
            return self
        params = iter(self.__params)

        def substitute(match: re.Match) -> str:
            directive = match[1]
            if directive == "%":
                return "%%"
            if directive == "s":
                literal = _sql.Literal(next(params)).as_string(cr.connection)
                return literal.replace("%", "%%")
            raise ValueError(
                f"SQL.inlined(): unsupported format directive "
                f"%{directive} in {self.__code!r}"
            )

        code = _PRINTF_DIRECTIVE_RE.sub(substitute, self.__code)
        return SQL(code, to_flush=self.__to_flush)

    def __repr__(self) -> str:
        return f"SQL({', '.join(map(repr, [self.__code, *self.__params]))})"

    def __bool__(self) -> bool:
        return bool(self.__code)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SQL)
            and self.__code == other.__code
            and self.__params == other.__params
        )

    def __hash__(self) -> int:
        return hash((self.__code, self.__params))

    def __iter__(self) -> Iterator:
        warnings.warn(
            "Deprecated since 19.0, use code and params properties directly",
            DeprecationWarning,
            stacklevel=2,
        )
        yield self.code
        yield self.params

    def join(self, args: Iterable) -> SQL:
        items = args if isinstance(args, list) else list(args)
        if len(items) == 0:
            return SQL.EMPTY
        if len(items) == 1 and isinstance(items[0], SQL):
            return items[0]
        if not self.__params:
            return SQL(
                self.__code.join("%s" for _ in items),
                *items,
                to_flush=self.__to_flush * (len(items) - 1) if items else (),
            )
        result = [self] * (len(items) * 2 - 1)
        for index, arg in enumerate(items):
            result[index * 2] = arg
        return SQL("%s" * len(result), *result)

    EMPTY: SQL

    @classmethod
    def identifier(
        cls,
        name: str,
        subname: str | None = None,
        to_flush: Field | None = None,
    ) -> SQL:
        if not (name.isidentifier() or IDENT_RE.match(name)):
            raise ValueError(f"{name!r} invalid for SQL.identifier()")
        if subname is None:
            return cls(f'"{name}"', to_flush=to_flush)
        if not (subname.isidentifier() or IDENT_RE.match(subname)):
            raise ValueError(f"{subname!r} invalid for SQL.identifier()")
        return cls(f'"{name}"."{subname}"', to_flush=to_flush)

    @classmethod
    def literal(cls, value: str) -> SQL:
        if not isinstance(value, str):
            raise TypeError(
                f"SQL.literal() expected str, got {type(value).__name__}: {value!r}"
            )
        if "'" in value or "\\" in value or "%" in value:
            raise ValueError(f"{value!r} invalid for SQL.literal()")
        return cls(f"'{value}'")

    @classmethod
    def in_(cls, lhs: SQL, values: Iterable) -> SQL:
        values = list(values)
        if not values:
            return cls("FALSE")
        return cls("%s = ANY(%s)", lhs, values)

    @classmethod
    def not_in(cls, lhs: SQL, values: Iterable) -> SQL:
        values = list(values)
        if not values:
            return cls("TRUE")
        return cls("%s <> ALL(%s)", lhs, values)


SQL.EMPTY = SQL()
