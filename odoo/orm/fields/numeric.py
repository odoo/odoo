import typing
from decimal import Decimal
from operator import attrgetter
from typing import override

from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_round
from odoo.tools.misc import PENDING, SENTINEL, Sentinel

from ..primitives import SEQUENCE_FIELD
from .base import Field, _prepare_fast_get

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, Environment, ModelClass, ModelLike, ModelType

MAXINT = 2**31 - 1

_debug = DebugLog(__name__)


def _float_to_pg_text(value: float) -> str:
    text = repr(float(value))
    return text.removesuffix(".0")


def _is_exact_number(value) -> bool:
    return value.__class__ in (int, float) or isinstance(value, Decimal)


class Integer(Field[int]):
    type = "integer"
    is_integer = True
    _column_type = ("int4", "int4")
    falsy_value = 0
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True

    aggregator: str | None = "sum"

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(lambda field, value, record: value or 0)

    def _get_attrs(self, model_class: ModelClass, name: str) -> dict[str, typing.Any]:
        res = super()._get_attrs(model_class, name)
        if "aggregator" not in res and name == SEQUENCE_FIELD:
            res["aggregator"] = None
            _debug.logic(
                "field.integer.sequence_aggregator_dropped",
                model=model_class._name,
                field=name,
            )
        return res

    @override
    def convert_to_column(
        self,
        value,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        return int(value or 0)

    @override
    def convert_to_cache(
        self, value, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        if value.__class__ is int:
            return value
        if isinstance(value, dict):
            return value.get("id") or 0
        return int(value or 0)

    @override
    def _comparand_to_column(self, value, model) -> typing.Any:
        if _is_exact_number(value):
            return value
        return super()._comparand_to_column(value, model)

    @override
    def _get_inequality_comparand(self, value, model) -> typing.Any:
        if _is_exact_number(value):
            return value or 0
        return super()._get_inequality_comparand(value, model)

    @override
    def convert_to_record(self, value, record: ModelLike) -> int:
        return value or 0

    @override
    def _get_pattern_text(self, cache_value: typing.Any) -> str:
        if cache_value is None:
            return ""
        return str(cache_value)

    @override
    def convert_to_read(
        self, value, record: ModelLike, use_display_name: bool = True
    ) -> typing.Any:
        if value and not (-MAXINT - 1 <= value <= MAXINT):
            _debug.logic(
                "field.integer.read_as_float",
                model=self.model_name,
                field=self.name,
                record=record.id,
            )
            return float(value)
        return value

    @override
    def convert_to_export(self, value, record: ModelLike) -> typing.Any:
        if value or value == 0:
            return value
        return ""


class Float(Field[float]):
    type = "float"
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _digits: str | tuple[int, int] | bool | None = None
    _min_display_digits: str | int | None = None
    falsy_value = 0.0
    aggregator: str | None = "sum"

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(lambda field, value, record: value or 0.0)

    def __init__(
        self,
        string: str | Sentinel = SENTINEL,
        digits: str | tuple[int, int] | Sentinel | bool | None = SENTINEL,
        min_display_digits: str | int | Sentinel | None = SENTINEL,
        **kwargs,
    ):
        if digits is SENTINEL and min_display_digits is not SENTINEL:
            digits = False
        super().__init__(
            string=string,
            _digits=digits,
            _min_display_digits=min_display_digits,
            **kwargs,
        )

    @property
    def _column_type(self) -> tuple[str, str]:  # type: ignore[override]
        return (
            ("numeric", "numeric")
            if self._digits is not None
            else ("float8", "double precision")
        )

    def get_digits(self, env: Environment) -> tuple[int, int] | bool | None:
        if isinstance(self._digits, str):
            precision = env.registry.locale.decimal_precision(env, self._digits)
            return 16, precision
        else:
            return self._digits

    _related__digits = property(attrgetter("_digits"))

    def _description_digits(self, env: Environment) -> tuple[int, int] | bool | None:
        return self.get_digits(env)

    def get_min_display_digits(self, env: Environment) -> int | None:
        if isinstance(self._min_display_digits, str):
            return env.registry.locale.decimal_precision(env, self._min_display_digits)
        return self._min_display_digits

    def _description_min_display_digits(self, env: Environment) -> int | None:
        return self.get_min_display_digits(env)

    @override
    def convert_to_column(
        self,
        value,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        value = float(value or 0.0)
        if isinstance(digits := self.get_digits(record.env), tuple):
            _precision, scale = digits
            value = float_round(value, precision_digits=scale)
        column_type = self.column_type
        if column_type is not None and column_type[0] == "numeric":
            return Decimal(repr(value))
        return value

    @override
    def convert_to_cache(
        self, value, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        if value.__class__ is float and self._digits is None:
            return value
        value = float(value or 0.0)
        digits = self._digits
        if digits is None:
            return value
        if isinstance(digits, tuple):
            return float_round(value, precision_digits=digits[1])
        if not isinstance(digits, str):
            return value
        precision = record.env.registry.locale.decimal_precision(record.env, digits)
        return float_round(value, precision_digits=precision)

    @override
    def _comparand_to_column(self, value, model) -> typing.Any:
        if not _is_exact_number(value):
            return super()._comparand_to_column(value, model)
        column_type = self.column_type
        if (
            column_type is not None
            and column_type[0] == "numeric"
            and not isinstance(value, Decimal)
        ):
            return Decimal(repr(float(value)))
        return float(value)

    @override
    def _get_inequality_comparand(self, value, model) -> typing.Any:
        if _is_exact_number(value):
            return float(value) or 0.0
        return super()._get_inequality_comparand(value, model)

    @override
    def convert_to_record(self, value, record: ModelLike) -> float:
        return value or 0.0

    @override
    def _get_pattern_text(self, cache_value: typing.Any) -> str:
        if cache_value is None:
            return ""
        return _float_to_pg_text(cache_value)

    @override
    def convert_to_export(self, value, record: ModelLike) -> typing.Any:
        if value or value == 0.0:  # noqa: RUF069  0.0 exactly, to tell a real zero from an empty value
            return value
        return ""

    round = staticmethod(float_round)
    compare = staticmethod(float_compare)


class Monetary(Field[float]):
    type = "monetary"
    is_monetary = True
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    write_sequence = 10
    _column_type = ("numeric", "numeric")
    falsy_value = 0.0

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(lambda field, value, record: value or 0.0)

    currency_field: str | None = None
    aggregator: str | None = "sum"

    def __init__(
        self,
        string: str | Sentinel = SENTINEL,
        currency_field: str | Sentinel = SENTINEL,
        **kwargs,
    ):
        super().__init__(string=string, currency_field=currency_field, **kwargs)

    def _description_currency_field(self, env: Environment) -> str | None:
        return self.get_currency_field(env[self.model_name])

    @override
    def _dynamic_description_attrs(self, env: Environment) -> frozenset[str]:
        dynamic = super()._dynamic_description_attrs(env)
        if not self.aggregator:
            return dynamic
        model = env[self.model_name]
        currency_field = model._fields[self._get_currency_field_name(model)]
        if not currency_field.column_type or not currency_field.store:
            return dynamic | {"aggregator"}
        return dynamic

    def _description_aggregator(self, env: Environment) -> str | None:
        model = env[self.model_name]
        currency_field_name = self._get_currency_field_name(model)
        currency_field = model._fields[currency_field_name]
        if not currency_field.column_type or not currency_field.store:
            try:
                query = model._as_query(ordered=False)
                model._read_group_select(
                    f"{currency_field_name}:array_agg_distinct", query
                )
            except (ValueError, AccessError, NotImplementedError) as e:
                _debug.logic(
                    "field.monetary.aggregator_unsupported",
                    model=self.model_name,
                    field=self.name,
                    currency_field=currency_field_name,
                    error=type(e).__name__,
                )
                return None

        return super()._description_aggregator(env)

    def get_currency_field(self, model: ModelLike) -> str | None:
        return self.currency_field or (
            "currency_id"
            if "currency_id" in model._fields
            else "x_currency_id"
            if "x_currency_id" in model._fields
            else None
        )

    def _get_currency_field_name(self, model: ModelLike) -> str:
        name = self.get_currency_field(model)
        if name is None:
            raise TypeError(
                f"Field {self} needs a currency field and {model._name} declares "
                f"neither currency_id nor x_currency_id"
            )
        return name

    def _resolve_currency_record(self, record: ModelLike):
        currency_field_name = self.get_currency_field(record)
        if not currency_field_name:
            return None
        return (
            record[:1]
            .with_prefetch(record._prefetch_ids)
            .with_env(record.env._derive(su=True, prefetch_fields=False))
        )[currency_field_name]

    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        assert self.get_currency_field(model) in model._fields, (
            f"Field {self} with unknown currency_field {self.get_currency_field(model)!r}"
        )

    def setup_related(self, model: BaseModel) -> None:
        super().setup_related(model)
        if self.inherited:
            self.currency_field = self.related_field.get_currency_field(
                model.env[self.related_field.model_name]
            )
            _debug.logic(
                "field.monetary.currency_field_inherited",
                model=self.model_name,
                field=self.name,
                currency_field=self.currency_field,
                related_model=self.related_field.model_name,
            )
        assert self.get_currency_field(model) in model._fields, (
            f"Field {self} with unknown currency_field {self.get_currency_field(model)!r}"
        )

    @override
    def convert_to_column(
        self,
        value,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        value = float(value or 0.0)
        if not value:
            return value
        if record.ids:
            currency = self._resolve_currency_record(record)
            if currency:
                return currency.with_env(record.env).round(value)
        return value

    def convert_to_column_insert(
        self,
        value,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        currency_field_name = self._get_currency_field_name(record)
        currency_field = record._fields[currency_field_name]
        if values and currency_field_name in values:
            dummy = record.new({currency_field_name: values[currency_field_name]})
            currency = dummy[currency_field_name]
            currency_from = "values"  # debuglog
        elif (
            values
            and currency_field.related
            and currency_field.related.split(".")[0] in values
        ):
            related_field_name = currency_field.related.split(".")[0]
            dummy = record.new({related_field_name: values[related_field_name]})
            currency = dummy[currency_field_name]
            currency_from = "related_values"  # debuglog
        else:
            currency = self._resolve_currency_record(record).with_env(record.env)
            currency_from = "record"  # debuglog

        if _debug.logic.enabled:
            _debug.logic(
                "field.monetary.insert_currency",
                model=self.model_name,
                field=self.name,
                currency_field=currency_field_name,
                currency_from=currency_from,
                currency=currency.id if currency else None,
            )
        value = float(value or 0.0)
        if currency:
            return currency.round(value)
        return value

    @override
    def convert_to_cache(
        self, value, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        value = float(value or 0.0)
        if value and validate:
            currency_field = self._get_currency_field_name(record)
            currency = record.with_env(
                record.env._derive(su=True, prefetch_fields=False)
            )[currency_field]
            if len(currency) > 1:
                raise ValueError(
                    "Got multiple currencies while assigning values of monetary field %s"
                    % str(self)
                )
            if currency:
                value = currency.with_env(record.env).round(value)
        return value

    @override
    def _comparand_to_column(self, value, model) -> typing.Any:
        if not _is_exact_number(value):
            return super()._comparand_to_column(value, model)
        return Decimal(repr(float(value))) if not isinstance(value, Decimal) else value

    @override
    def _get_inequality_comparand(self, value, model) -> typing.Any:
        if _is_exact_number(value):
            return float(value) or 0.0
        return super()._get_inequality_comparand(value, model)

    @override
    def convert_to_record(self, value, record: ModelLike) -> float:
        return value or 0.0

    @override
    def _get_pattern_text(self, cache_value: typing.Any) -> str:
        if cache_value is None:
            return ""
        return _float_to_pg_text(cache_value)

    @override
    def convert_to_read(
        self, value, record: ModelLike, use_display_name: bool = True
    ) -> typing.Any:
        return value

    @override
    def convert_to_write(self, value, record: ModelLike) -> typing.Any:
        return value

    @override
    def convert_to_export(self, value, record: ModelLike) -> typing.Any:
        if value or value == 0.0:  # noqa: RUF069  0.0 exactly, to tell a real zero from an empty value
            return value
        return ""

    def _filter_not_equal(
        self, records: ModelType, cache_value: typing.Any
    ) -> ModelType:
        records = super()._filter_not_equal(records, cache_value)
        if not records:
            return records
        env = records.env
        field_cache = self._get_cache(env)
        currency_field = records._fields[self._get_currency_field_name(records)]
        ids_to_update = tuple(
            record_id
            for record_id, record_sudo in zip(
                records._ids,
                records.sudo().with_context(prefetch_fields=False),
                strict=False,
            )
            if not (
                (value := field_cache.get(record_id))
                and value is not PENDING
                and (currency := currency_field.__get__(record_sudo))
                and currency.with_env(env).round(value) == cache_value
            )
        )
        if _debug.logic.enabled and len(ids_to_update) < len(records):
            _debug.logic(
                "field.monetary.rounded_equal_skipped",
                model=self.model_name,
                field=self.name,
                records=len(records),
                changed=len(ids_to_update),
            )
        return records._spawn(env, ids_to_update, records._prefetch_ids)
