import fnmatch
import operator as pyoperator
import re
import typing
import warnings
from collections.abc import (
    Callable,
)
from collections.abc import Set as AbstractSet

from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    SQL,
    Query,
)
from odoo.tools.misc import PENDING, SENTINEL

from ..domain import Domain
from ..domain.constants import REGEX_CONDITION_OPERATORS
from ..primitives import COLLECTION_TYPES, SQL_OPERATORS
from ._field_stubs import _FieldStubs

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, Field, ModelLike
    from ..domain.ast import DomainCondition, OptimizationLevel

    M = typing.TypeVar("M", bound=BaseModel)


PYTHON_INEQUALITY_OPERATOR: dict[str, Callable[[typing.Any, typing.Any], bool]] = {
    "<": pyoperator.lt,
    ">": pyoperator.gt,
    "<=": pyoperator.le,
    ">=": pyoperator.ge,
}

IN_TO_ANY_THRESHOLD = 100

_debug = DebugLog(__name__)


def _get_like_regex(value: str, exact: bool) -> str:
    if not exact:
        value = f"%{value}%"
    parts = []
    escaped = False
    for char in value:
        if not escaped and char == "\\":
            escaped = True
            continue
        if not escaped and char == "%":
            parts.append("*")
        elif not escaped and char == "_":
            parts.append("?")
        else:
            parts.append(f"[{char}]" if char in "*?[" else char)
        escaped = False
    if escaped:
        raise ValueError("LIKE pattern must not end with an escape character")
    return fnmatch.translate("".join(parts))


class _FieldSqlMixin(_FieldStubs):
    _fetch_term: SQL | None = None
    _column_term: SQL | None = None
    _fetch_terms_by_langs: dict[tuple[str, ...], SQL] | None = None

    def to_sql(self, model: ModelLike, alias: str) -> SQL:
        if not self.store or not self.column_type:
            raise ValueError(f"Cannot convert {self} to SQL because it is not stored")
        sql_field = SQL.identifier(
            alias, self.name, to_flush=typing.cast("Field", self)
        )
        if self.company_dependent:
            underlying = self._column_type
            if underlying is None:
                raise ValueError(
                    f"Cannot convert {self} to SQL: it is company-dependent, so "
                    f"its column is jsonb and the casts below need the "
                    f"underlying column type, which it does not declare"
                )
            fallback = self.get_company_dependent_fallback(model)
            fallback = self.convert_to_column(
                self.convert_to_write(fallback, model), model
            )
            _debug.logic(
                "field.sql.company_dependent.coalesced",
                model=model._name,
                field=self.name,
                company=model.env.company.id,
                column_type=underlying[1],
                has_fallback=fallback is not None,
            )
            sql_field = SQL(
                "COALESCE(%(column)s->%(company_id)s,to_jsonb(%(fallback)s::%(column_type)s))",
                column=sql_field,
                company_id=str(model.env.company.id),
                fallback=fallback,
                column_type=SQL(underlying[1]),
            )
            if self.type in ("boolean", "integer", "float", "monetary"):
                return SQL("(%s)::%s", sql_field, SQL(underlying[1]))
            return SQL("(%s->>0)::%s", sql_field, SQL(underlying[1]))

        return sql_field

    def property_to_sql(
        self,
        field_sql: SQL,
        property_name: str,
        model: ModelLike,
        alias: str,
        query: Query,
    ) -> SQL:
        raise ValueError(f"Invalid field property {property_name!r} on {self}")

    def _comparand_to_column(self, value: typing.Any, model: BaseModel) -> typing.Any:
        return self.convert_to_column(value, model, validate=False)

    def _get_inequality_comparand(
        self, value: typing.Any, model: BaseModel
    ) -> typing.Any:
        return self.convert_to_cache(value, model) or self.falsy_value

    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        return condition

    def condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        sql_expr = self._condition_to_sql(
            field_expr, operator, value, model, alias, query
        )
        if self.company_dependent:
            sql_expr = self._condition_to_sql_company(
                sql_expr, field_expr, operator, value, model, alias, query
            )
        return sql_expr

    def _get_comparand_converter(self, field_expr: str, model: BaseModel):
        if field_expr == self.name:
            return lambda v: self._comparand_to_column(v, model)
        return lambda v: v

    def _condition_in_to_sql(
        self, sql_field: SQL, operator: str, value, _value_to_column, can_be_null: bool
    ) -> SQL:
        assert isinstance(value, COLLECTION_TYPES), (
            f"condition_to_sql() 'in' operator expects a collection, not a {value!r}"
        )
        converted: list[typing.Any] = []
        null_in_condition = False
        dropped = 0  # debuglog
        for v in value:
            if v is False or v is None:
                null_in_condition = True
                continue
            try:
                converted.append(_value_to_column(v))
            except ValueError, TypeError:
                dropped += 1  # debuglog
                continue
        if _debug.logic.enabled and dropped:
            _debug.logic(
                "field.sql.in.values_dropped",
                model=self.model_name,
                field=self.name,
                operator=operator,
                dropped=dropped,
                kept=len(converted),
            )
        params = tuple(converted)
        if not params and not null_in_condition:
            _debug.logic(
                "field.sql.in.constant",
                model=self.model_name,
                field=self.name,
                operator=operator,
            )
            return SQL("FALSE") if operator == "in" else SQL("TRUE")
        if (null_value := self.falsy_value) is not None:
            null_value = _value_to_column(null_value)
            if null_value in params:
                null_in_condition = True
            elif null_in_condition:
                params = (*params, null_value)

        sql = None
        if params:
            if len(params) > IN_TO_ANY_THRESHOLD:
                _debug.logic(
                    "field.sql.in.any_rewrite",
                    model=self.model_name,
                    field=self.name,
                    operator=operator,
                    values=len(params),
                )
                anyall = "= ANY(%s)" if operator == "in" else "!= ALL(%s)"
                sql = SQL(f"%s {anyall}", sql_field, list(params))
            else:
                sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], params)

        if (operator == "in") == null_in_condition:
            if not can_be_null:
                return sql or SQL("FALSE")
            sql_null = SQL("%s IS NULL", sql_field)
            return SQL("(%s OR %s)", sql, sql_null) if sql else sql_null

        elif operator == "not in" and null_in_condition and not sql:
            return SQL("%s IS NOT NULL", sql_field) if can_be_null else SQL("TRUE")

        assert sql, f"Missing sql query for {operator} {value!r}"
        return sql

    def _condition_like_to_sql(
        self, sql_field: SQL, operator: str, value, model: BaseModel, can_be_null: bool
    ) -> SQL:
        sql_left = sql_field if self.is_text else SQL("%s::text", sql_field)

        need_wildcard = "=" not in operator
        if need_wildcard:
            sql_value = SQL("%s", f"%{value}%")
        else:
            sql_value = SQL("%s", str(value))
        if operator.endswith("ilike"):
            sql_left = model.env.registry.unaccent(sql_left)
            sql_value = model.env.registry.unaccent(sql_value)

        sql = SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], sql_value)
        _debug.logic(
            "field.sql.like",
            model=self.model_name,
            field=self.name,
            operator=operator,
            cast_to_text=not self.is_text,
            unaccent=operator.endswith("ilike"),
            null_accepted=operator in Domain.NEGATIVE_OPERATORS and can_be_null,
        )
        if operator in Domain.NEGATIVE_OPERATORS and can_be_null:
            sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
        return sql

    def _condition_regex_to_sql(
        self, sql_field: SQL, operator: str, value, can_be_null: bool
    ) -> SQL:
        sql_left = sql_field if self.is_text else SQL("%s::text", sql_field)
        sql = SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], str(value))
        if operator in Domain.NEGATIVE_OPERATORS and can_be_null:
            sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
        return sql

    def _condition_inequality_to_sql(
        self,
        sql_field: SQL,
        operator: str,
        value,
        model: BaseModel,
        _value_to_column,
        can_be_null: bool,
    ) -> SQL:
        accept_null_value = False
        if (null_value := self.falsy_value) is not None:
            value = self._get_inequality_comparand(value, model)
            accept_null_value = can_be_null and PYTHON_INEQUALITY_OPERATOR[operator](
                null_value, value
            )
        sql_value = SQL("%s", _value_to_column(value))

        sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], sql_value)
        if accept_null_value:
            _debug.logic(
                "field.sql.inequality.null_accepted",
                model=self.model_name,
                field=self.name,
                operator=operator,
            )
            sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
        return sql

    @staticmethod
    def _condition_any_to_sql(sql_field: SQL, operator: str, value) -> SQL:
        if isinstance(value, Query):
            subselect = value.subselect()
        elif isinstance(value, SQL):
            subselect = SQL("(%s)", value)
        else:
            raise TypeError(
                f"condition_to_sql() operator 'any!' accepts SQL or Query, got {value}"
            )
        sql_operator = SQL_OPERATORS["in" if operator == "any!" else "not in"]
        return SQL("%s%s%s", sql_field, sql_operator, subselect)

    def _condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value: typing.Any,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        sql_field = model._field_to_sql(alias, field_expr, query)
        _value_to_column = self._get_comparand_converter(field_expr, model)

        if operator in SQL_OPERATORS and isinstance(value, SQL):
            _debug.logic(
                "field.sql.raw_sql_comparand",
                model=model._name,
                field_expr=field_expr,
                operator=operator,
            )
            warnings.warn(
                "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
                DeprecationWarning,
                stacklevel=2,
            )
            return SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], value)

        can_be_null = self not in model.env.registry.not_null_fields

        if operator in ("in", "not in"):
            return self._condition_in_to_sql(
                sql_field, operator, value, _value_to_column, can_be_null
            )

        if operator.endswith("like"):
            return self._condition_like_to_sql(
                sql_field, operator, value, model, can_be_null
            )

        if operator in REGEX_CONDITION_OPERATORS:
            return self._condition_regex_to_sql(sql_field, operator, value, can_be_null)

        if operator in (">", "<", ">=", "<="):
            return self._condition_inequality_to_sql(
                sql_field, operator, value, model, _value_to_column, can_be_null
            )

        if operator in ("any!", "not any!"):
            return self._condition_any_to_sql(sql_field, operator, value)

        raise NotImplementedError(
            f"Invalid operator {operator!r} for SQL in domain term {(field_expr, operator, value)!r}"
        )

    def _condition_to_sql_company(
        self,
        sql_expr: SQL,
        field_expr: str,
        operator: str,
        value: typing.Any,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        if (
            self.company_dependent
            and self.index == "btree_not_null"
            and not (self.is_temporal and field_expr != self.name)
            and model.env.registry.metaschema.evaluate_default_condition(
                model.env, model._name, field_expr, operator, value
            )
            is False
        ):
            _debug.logic(
                "field.sql.company_dependent.fallback_excluded",
                model=self.model_name,
                field=self.name,
                operator=operator,
            )
            return SQL(
                "(%s IS NOT NULL AND %s)",
                SQL.identifier(alias, self.name),
                sql_expr,
            )
        return sql_expr

    def get_expression_getter(
        self, field_expr: str
    ) -> Callable[[BaseModel], typing.Any]:
        if field_expr == self.name:
            return self.__get__
        raise ValueError(f"Expression not supported on {self}: {field_expr!r}")

    def _get_pattern_text(self, cache_value: typing.Any) -> str:
        if cache_value is None or cache_value is False:
            return ""
        return str(cache_value)

    def _get_pattern_getter(
        self, records: M, field_expr: str, getter: Callable[[M], typing.Any]
    ) -> Callable[[M], str]:
        pattern_text = self._get_pattern_text
        if field_expr != self.name or callable(self.translate):
            return lambda rec: pattern_text(getter(rec))

        env = records.env
        _MISSING = SENTINEL
        _PENDING = PENDING
        get_cache = self._get_cache

        def render(rec: M) -> str:
            value = get_cache(env).get(rec._ids[0], _MISSING)
            if value is _MISSING or value is _PENDING:
                record_value = getter(rec)
                value = get_cache(env).get(rec._ids[0], _MISSING)
                if value is _MISSING:
                    return pattern_text(record_value)
            return pattern_text(value)

        return render

    def _filter_in(self, getter, value) -> Callable:
        assert isinstance(value, COLLECTION_TYPES) and value, (
            f"filter_function() 'in' operator expects a collection, not a {type(value)}"
        )
        if not isinstance(value, AbstractSet):
            value = set(value)
        if False in value or self.falsy_value in value:
            if len(value) == 1:
                return lambda rec: not getter(rec)
            return lambda rec: (val := getter(rec)) in value or not val
        return lambda rec: getter(rec) in value

    def _filter_like(
        self, records: M, field_expr: str, getter, operator: str, value
    ) -> Callable:
        if operator.endswith("ilike"):
            unaccent = records.env.registry.get_ilike_normalizer(records.env)

        else:

            def unaccent(x):
                return x

        pattern = value if isinstance(value, str) else self._get_pattern_text(value)
        like_regex = re.compile(
            _get_like_regex(unaccent(pattern), "=" in operator),
        )
        render = self._get_pattern_getter(records, field_expr, getter)
        return lambda rec: like_regex.match(unaccent(render(rec)))

    def _filter_regex(self, records: M, field_expr: str, getter, value) -> Callable:
        regex = re.compile(str(value))
        render = self._get_pattern_getter(records, field_expr, getter)
        return lambda rec: regex.search(render(rec)) is not None

    def _filter_inequality(self, records: M, getter, pyop, value) -> Callable:
        can_be_null = False
        if (null_value := self.falsy_value) is not None:
            value = self._get_inequality_comparand(value, records)
            can_be_null = pyop(null_value, value)

        def is_inequality_satisfied(rec):
            rec_value = getter(rec)
            try:
                if rec_value is False or rec_value is None:
                    return can_be_null
                return pyop(rec_value, value)
            except ValueError, TypeError:
                return False

        return is_inequality_satisfied

    def filter_function(
        self, records: M, field_expr: str, operator: str, value: typing.Any
    ) -> Callable[[M], bool]:
        assert operator not in Domain.NEGATIVE_OPERATORS, (
            "only positive operators are implemented"
        )
        getter = self.get_expression_getter(field_expr)

        if operator == "in":
            return self._filter_in(getter, value)

        if operator.endswith("like"):
            return self._filter_like(records, field_expr, getter, operator, value)

        if operator == "=~":
            return self._filter_regex(records, field_expr, getter, value)

        if pyop := PYTHON_INEQUALITY_OPERATOR.get(operator):
            return self._filter_inequality(records, getter, pyop, value)

        raise NotImplementedError(f"Invalid simple operator {operator!r}")
