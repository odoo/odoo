import contextlib
import typing
from typing import override

from psycopg.types.json import Json as PsycopgJson

from odoo.libs.debug_log import DebugLog
from odoo.libs.json import dumps as _fast_dumps
from odoo.libs.json import fast_clone
from odoo.libs.json import loads as _fast_loads
from odoo.tools import SQL
from odoo.tools.json import orjson_default

from ..primitives import COLLECTION_TYPES, IdType, NewId
from ._field_sql import PYTHON_INEQUALITY_OPERATOR
from .base import Field, _prepare_fast_get

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from .._typing import ModelLike
    from ..models import BaseModel

_debug = DebugLog(__name__)


class Boolean(Field[bool]):
    type = "boolean"
    is_boolean = True
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_read_value = True

    cache_is_orderable = False
    """Not this one, and not for lack of trying.

    ``sort_ids_by_cache`` groups *falsy* cache values with NULL so that an
    in-memory sort reproduces PostgreSQL's null ordering (ASC NULLS LAST). For
    every other scannable type the falsy value *is* the null -- ``""`` for a
    Char, ``None`` for a Date -- so the two are interchangeable. For a Boolean
    they are not: ``False`` is a value, and lumping it with NULL puts it at the
    far end from where it belongs. Measured on four records
    (True, False, True, NULL): the cache sort ascending returns
    ``[True, True, False, NULL]`` where the field returns
    ``[False, NULL, True, True]``.
    """
    _column_type = ("bool", "bool")
    falsy_value = False

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(
            lambda field, value, record: False if value is None else value
        )

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> bool:
        return bool(value)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> bool:
        return bool(value)

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> bool:
        return bool(value)

    @override
    def _condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value: typing.Any,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        if operator not in ("in", "not in"):
            return super()._condition_to_sql(
                field_expr, operator, value, model, alias, query
            )

        sql_field = model._field_to_sql(alias, field_expr, query)

        possible_values = (
            {bool(v) for v in value}
            if operator == "in"
            else {True, False} - {bool(v) for v in value}
        )
        if len(possible_values) != 1:
            _debug.logic(
                "field.boolean.condition_constant",
                model=model._name,
                field_expr=field_expr,
                operator=operator,
                constant=bool(possible_values),
            )
            return SQL("TRUE") if possible_values else SQL("FALSE")
        is_true = True in possible_values
        return (
            SQL("%s IS TRUE", sql_field)
            if is_true
            else SQL("%s IS NOT TRUE", sql_field)
        )


class Json(Field):
    type = "json"
    cache_truthiness_matches = True
    _column_type = ("jsonb", "jsonb")

    @override
    def convert_to_record(self, value: typing.Any, record: ModelLike) -> typing.Any:
        return False if value is None else fast_clone(value)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        if not value:
            return None
        return _fast_loads(_fast_dumps(value, default=orjson_default))

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if validate:
            value = self.convert_to_cache(value, record)
        if value is None:
            return None
        return PsycopgJson(value)

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> str:
        if not value:
            return ""
        return _fast_dumps(value, default=orjson_default)


class Id(Field[IdType | typing.Literal[False]]):
    type = "integer"
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _register_type = False
    column_type = ("int4", "int4")

    string = "ID"
    store = True
    readonly = True
    prefetch = False

    def update_db(self, model: ModelLike, columns: dict[str, typing.Any]) -> bool:
        return False

    @typing.overload
    def __get__(self, record: None, owner: typing.Any = None) -> typing.Self: ...
    @typing.overload
    def __get__(
        self, record: BaseModel, owner: typing.Any = None
    ) -> IdType | typing.Literal[False]: ...
    @typing.overload
    def __get__(self, record: object, owner: typing.Any = None) -> typing.Any: ...

    @override
    def __get__(
        self, record: typing.Any, owner: typing.Any = None
    ) -> IdType | typing.Literal[False] | typing.Self:
        if record is None:
            return self

        ids = record._ids
        size = len(ids)
        if size == 0:
            return False
        elif size == 1:
            return ids[0]
        raise ValueError(f"Expected singleton: {record}")

    @override
    def __set__(self, record: BaseModel, value: typing.Any) -> None:
        msg = "field 'id' cannot be assigned"
        raise TypeError(msg)

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if value is None or value is False:
            return None
        if isinstance(value, NewId):
            return value
        if not record._auto:
            return value
        if value is True:
            raise ValueError(f"Invalid id value for {self}: {value!r}")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                pass
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid id value for {self}: {value!r}") from None
        raise ValueError(f"Invalid id value for {self}: {value!r}")

    def to_sql(self, model: ModelLike, alias: str) -> SQL:
        assert self.store, "id field must be stored"
        return SQL.identifier(alias, self.name)

    @override
    def filter_function(
        self,
        records: BaseModel,
        field_expr: str,
        operator: str,
        value: typing.Any,
    ) -> typing.Any:
        if operator == "in" and isinstance(value, COLLECTION_TYPES):
            if any(v.__class__ is str for v in value):
                coerced = set()
                for v in value:
                    with contextlib.suppress(ValueError):
                        coerced.add(self.convert_to_column(v, records, validate=False))
                _debug.logic(
                    "field.id.filter_values_coerced",
                    model=records._name,
                    given=len(value),
                    coerced=len(coerced),
                )
                if not coerced:
                    return lambda _: False
                value = coerced
        elif value.__class__ is str and operator in PYTHON_INEQUALITY_OPERATOR:
            value = self.convert_to_column(value, records, validate=False)
        return super().filter_function(records, field_expr, operator, value)

    @override
    def get_expression_getter(self, field_expr: str) -> typing.Any:
        if field_expr != "id.origin":
            return super().get_expression_getter(field_expr)

        def getter(record: BaseModel) -> typing.Any:
            ids = record._ids
            if not ids:
                return False
            return (id_ := ids[0]) or getattr(id_, "origin", None) or False

        return getter
