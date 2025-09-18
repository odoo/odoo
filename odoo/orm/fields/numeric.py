import typing
from operator import attrgetter
from typing import override

from odoo.exceptions import AccessError
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.tools.misc import PENDING, SENTINEL, Sentinel

from .base import Field, _make_scalar_get

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, Environment

# Maximum value representable by XML-RPC's <i4> type (32-bit signed int).
# Values exceeding this are sent as floats to avoid XML-RPC transport errors.
MAXINT = 2**31 - 1


class Integer(Field[int]):
    """Encapsulates an :class:`int`."""

    type = "integer"
    _column_type = ("int4", "int4")
    falsy_value = 0

    aggregator = "sum"

    __get__ = _make_scalar_get(lambda v: v or 0)

    def _get_attrs(
        self, model_class: type[BaseModel], name: str
    ) -> dict[str, typing.Any]:
        res = super()._get_attrs(model_class, name)
        # The default aggregator is None for sequence fields
        if "aggregator" not in res and name == "sequence":
            res["aggregator"] = None
        return res

    @override
    def convert_to_column(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        return int(value or 0)

    @override
    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        # fast path: most writes already pass an int
        if value.__class__ is int:
            return value
        if isinstance(value, dict):
            # special case, when an integer field is used as inverse for a one2many
            return value.get("id", None)
        return int(value or 0)

    @override
    def convert_to_record(
        self, value, record: BaseModel
    ) -> int | typing.Literal[False]:
        return value or 0

    @override
    def convert_to_read(
        self, value, record: BaseModel, use_display_name: bool = True
    ) -> typing.Any:
        # Integer values greater than 2^31-1 are not supported in pure XMLRPC,
        # so we have to pass them as floats :-(
        if value and value > MAXINT:
            return float(value)
        return value

    def _update_inverse(self, records: BaseModel, value: BaseModel) -> None:
        self._update_cache(records, value.id or 0)

    @override
    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        if value or value == 0:
            return value
        return ""


class Float(Field[float]):
    """Encapsulates a :class:`float`.

    The precision digits are given by the (optional) ``digits`` attribute.

    :param digits: a pair (total, decimal) or a string referencing a
        :class:`~odoo.addons.base.models.decimal_precision.DecimalPrecision` record name.
    :type digits: tuple(int,int) or str

    When a float is a quantity associated with an unit of measure, it is important
    to use the right tool to compare or round values with the correct precision.

    The Float class provides some static methods for this purpose:

    :func:`~odoo.fields.Float.round()` to round a float with the given precision.
    :func:`~odoo.fields.Float.is_zero()` to check if a float equals zero at the given precision.
    :func:`~odoo.fields.Float.compare()` to compare two floats at the given precision.

    .. admonition:: Example

        To round a quantity with the precision of the unit of measure::

            fields.Float.round(self.product_uom_qty, precision_rounding=self.product_uom_id.rounding)

        To check if the quantity is zero with the precision of the unit of measure::

            fields.Float.is_zero(self.product_uom_qty, precision_rounding=self.product_uom_id.rounding)

        To compare two quantities::

            field.Float.compare(self.product_uom_qty, self.qty_done, precision_rounding=self.product_uom_id.rounding)

        The compare helper uses the __cmp__ semantics for historic purposes, therefore
        the proper, idiomatic way to use this helper is like so:

            if result == 0, the first and second floats are equal
            if result < 0, the first float is lower than the second
            if result > 0, the first float is greater than the second
    """

    type = "float"
    _digits: str | tuple[int, int] | None = (
        None  # digits argument passed to class initializer
    )
    _min_display_digits: str | int | None = None
    falsy_value = 0.0
    aggregator = "sum"

    __get__ = _make_scalar_get(lambda v: v or 0.0)

    def __init__(
        self,
        string: str | Sentinel = SENTINEL,
        digits: str | tuple[int, int] | Sentinel | None = SENTINEL,
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
    def _column_type(self) -> tuple[str, str]:
        # Explicit support for "falsy" digits (0, False) to indicate a NUMERIC
        # field with no fixed precision. The values are saved in the database
        # with all significant digits.
        # FLOAT8 type is still the default when there is no precision because it
        # is faster for most operations (sums, etc.)
        return (
            ("numeric", "numeric")
            if self._digits is not None
            else ("float8", "double precision")
        )

    def get_digits(self, env: Environment) -> tuple[int, int] | None:
        if isinstance(self._digits, str):
            precision = env["decimal.precision"].precision_get(self._digits)
            return 16, precision
        else:
            return self._digits

    _related__digits = property(attrgetter("_digits"))

    def _description_digits(self, env: Environment) -> tuple[int, int] | None:
        return self.get_digits(env)

    def get_min_display_digits(self, env: Environment) -> int | None:
        if isinstance(self._min_display_digits, str):
            return env["decimal.precision"].precision_get(self._min_display_digits)
        return self._min_display_digits

    def _description_min_display_digits(self, env: Environment) -> int | None:
        return self.get_min_display_digits(env)

    @override
    def convert_to_column(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        value = float(value or 0.0)
        if digits := self.get_digits(record.env):
            _precision, scale = digits
            value = float_round(value, precision_digits=scale)
        return value

    @override
    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        # Fast path: float with no digits constraint (most Float fields)
        if value.__class__ is float and self._digits is None:
            return value
        # apply rounding here, otherwise value in cache may be wrong!
        value = float(value or 0.0)
        # Fast path: inline digit resolution for the common tuple case
        digits = self._digits
        if digits is None:
            return value
        if isinstance(digits, tuple):
            return float_round(value, precision_digits=digits[1])
        if not isinstance(digits, str):
            # Falsy/integer digits (e.g., digits=0): NUMERIC with no fixed precision
            return value
        # String-referenced precision (rare): needs env lookup
        precision = record.env["decimal.precision"].precision_get(digits)
        return float_round(value, precision_digits=precision)

    @override
    def convert_to_record(
        self, value, record: BaseModel
    ) -> float | typing.Literal[False]:
        return value or 0.0

    @override
    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        if value or value == 0.0:
            return value
        return ""

    round = staticmethod(float_round)
    is_zero = staticmethod(float_is_zero)
    compare = staticmethod(float_compare)


class Monetary(Field[float]):
    """Encapsulates a :class:`float` expressed in a given
    :class:`res_currency<odoo.addons.base.models.res_currency.Currency>`.

    The decimal precision and currency symbol are taken from the ``currency_field`` attribute.

    :param str currency_field: name of the :class:`Many2one` field
        holding the :class:`res_currency <odoo.addons.base.models.res_currency.Currency>`
        this monetary field is expressed in (default: `\'currency_id\'`)
    """

    type = "monetary"
    write_sequence = 10
    _column_type = ("numeric", "numeric")
    falsy_value = 0.0

    __get__ = _make_scalar_get(lambda v: v or 0.0)

    currency_field: Field | None = None
    aggregator = "sum"

    def __init__(
        self,
        string: str | Sentinel = SENTINEL,
        currency_field: str | Sentinel = SENTINEL,
        **kwargs,
    ):
        super().__init__(string=string, currency_field=currency_field, **kwargs)

    def _description_currency_field(self, env: Environment) -> str | None:
        return self.get_currency_field(env[self.model_name])

    def _description_aggregator(self, env: Environment) -> str | None:
        model = env[self.model_name]
        query = model._as_query(ordered=False)
        currency_field_name = self.get_currency_field(model)
        currency_field = model._fields[currency_field_name]
        # The currency field needs to be aggregable too
        if not currency_field.column_type or not currency_field.store:
            try:
                model._read_group_select(
                    f"{currency_field_name}:array_agg_distinct", query
                )
            except ValueError, AccessError:
                return None

        return super()._description_aggregator(env)

    def get_currency_field(self, model: BaseModel) -> str | None:
        """Return the name of the currency field."""
        return self.currency_field or (
            "currency_id"
            if "currency_id" in model._fields
            else "x_currency_id" if "x_currency_id" in model._fields else None
        )

    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        assert (
            self.get_currency_field(model) in model._fields
        ), f"Field {self} with unknown currency_field {self.get_currency_field(model)!r}"

    def setup_related(self, model: BaseModel) -> None:
        super().setup_related(model)
        if self.inherited:
            self.currency_field = self.related_field.get_currency_field(
                model.env[self.related_field.model_name]
            )
        assert (
            self.get_currency_field(model) in model._fields
        ), f"Field {self} with unknown currency_field {self.get_currency_field(model)!r}"

    @override
    def convert_to_column(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        value = float(value or 0.0)
        if not value:
            return value
        # Apply currency rounding when record is actual (not model class).
        # This aligns with convert_to_column_insert for company-dependent
        # field paths (get_column_update, fallback comparison).
        if record.ids:
            currency_field_name = self.get_currency_field(record)
            if currency_field_name:
                currency = (
                    record[:1]
                    .sudo()
                    .with_context(prefetch_fields=False)[currency_field_name]
                )
                if currency:
                    return currency.with_env(record.env).round(value)
        return value

    def convert_to_column_insert(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        # retrieve currency from values or record
        currency_field_name = self.get_currency_field(record)
        currency_field = record._fields[currency_field_name]
        if values and currency_field_name in values:
            dummy = record.new({currency_field_name: values[currency_field_name]})
            currency = dummy[currency_field_name]
        elif (
            values
            and currency_field.related
            and currency_field.related.split(".")[0] in values
        ):
            related_field_name = currency_field.related.split(".")[0]
            dummy = record.new({related_field_name: values[related_field_name]})
            currency = dummy[currency_field_name]
        else:
            # Note: this is wrong if 'record' is several records with different
            # currencies, which is functional nonsense and should not happen
            # BEWARE: do not prefetch other fields, because 'value' may be in
            # cache, and would be overridden by the value read from database!
            currency = (
                record[:1]
                .sudo()
                .with_context(prefetch_fields=False)[currency_field_name]
            )
            currency = currency.with_env(record.env)

        value = float(value or 0.0)
        if currency:
            return currency.round(value)
        return value

    @override
    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        # cache format: float
        value = float(value or 0.0)
        if value and validate:
            # Currency field may not be initialized yet if it is a computed or
            # related field (e.g., during record creation before all fields are
            # set).  The prefetch_fields=False guard prevents reading unrelated
            # fields that could overwrite the value currently being cached.
            currency_field = self.get_currency_field(record)
            currency = record.sudo().with_context(prefetch_fields=False)[currency_field]
            if len(currency) > 1:
                raise ValueError(
                    "Got multiple currencies while assigning values of monetary field %s"
                    % str(self)
                )
            if currency:
                value = currency.with_env(record.env).round(value)
        return value

    @override
    def convert_to_record(
        self, value, record: BaseModel
    ) -> float | typing.Literal[False]:
        return value or 0.0

    @override
    def convert_to_read(
        self, value, record: BaseModel, use_display_name: bool = True
    ) -> typing.Any:
        return value

    @override
    def convert_to_write(self, value, record: BaseModel) -> typing.Any:
        return value

    @override
    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        if value or value == 0.0:
            return value
        return ""

    def _filter_not_equal(
        self, records: BaseModel, cache_value: typing.Any
    ) -> BaseModel:
        records = super()._filter_not_equal(records, cache_value)
        if not records:
            return records
        # check that the values were rounded properly when put in cache
        # see fix odoo/odoo#177200 (commit 7164d5295904b08ec3a0dc1fb54b217671ff531c)
        env = records.env
        field_cache = self._get_cache(env)
        currency_field = records._fields[self.get_currency_field(records)]
        return records.browse(
            record_id
            for record_id, record_sudo in zip(
                records._ids, records.sudo().with_context(prefetch_fields=False), strict=False
            )
            if not (
                (value := field_cache.get(record_id))
                and value is not PENDING
                and (currency := currency_field.__get__(record_sudo))
                and currency.with_env(env).round(value) == cache_value
            )
        )
