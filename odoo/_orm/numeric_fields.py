from operator import attrgetter
from xmlrpc.client import MAXINT  # TODO change this

from odoo.tools import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import SENTINEL, Sentinel

from .fields import Field


class Integer(Field[int]):
    """ Encapsulates an :class:`int`. """
    type = 'integer'
    _column_type = ('int4', 'int4')

    aggregator = 'sum'

    def _get_attrs(self, model_class, name):
        res = super()._get_attrs(model_class, name)
        # The default aggregator is None for sequence fields
        if 'aggregator' not in res and name == 'sequence':
            res['aggregator'] = None
        return res

    def convert_to_column(self, value, record, values=None, validate=True):
        return int(value or 0)

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, dict):
            # special case, when an integer field is used as inverse for a one2many
            return value.get('id', None)
        return int(value or 0)

    def convert_to_record(self, value, record):
        return value or 0

    def convert_to_read(self, value, record, use_display_name=True):
        # Integer values greater than 2^31-1 are not supported in pure XMLRPC,
        # so we have to pass them as floats :-(
        if value and value > MAXINT:
            return float(value)
        return value

    def _update(self, records, value):
        cache = records.env.cache
        for record in records:
            cache.set(record, self, value.id or 0)

    def convert_to_export(self, value, record):
        if value or value == 0:
            return value
        return ''


class Float(Field[float]):
    """ Encapsulates a :class:`float`.

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

    type = 'float'
    _digits = None                      # digits argument passed to class initializer
    aggregator = 'sum'

    def __init__(self, string: str | Sentinel = SENTINEL, digits: str | tuple[int, int] | None | Sentinel = SENTINEL, **kwargs):
        super(Float, self).__init__(string=string, _digits=digits, **kwargs)

    @property
    def _column_type(self):
        # Explicit support for "falsy" digits (0, False) to indicate a NUMERIC
        # field with no fixed precision. The values are saved in the database
        # with all significant digits.
        # FLOAT8 type is still the default when there is no precision because it
        # is faster for most operations (sums, etc.)
        return ('numeric', 'numeric') if self._digits is not None else \
               ('float8', 'double precision')

    def get_digits(self, env):
        if isinstance(self._digits, str):
            precision = env['decimal.precision'].precision_get(self._digits)
            return 16, precision
        else:
            return self._digits

    _related__digits = property(attrgetter('_digits'))

    def _description_digits(self, env):
        return self.get_digits(env)

    def convert_to_column(self, value, record, values=None, validate=True):
        value_float = value = float(value or 0.0)
        if digits := self.get_digits(record.env):
            precision, scale = digits
            value_float = float_round(value, precision_digits=scale)
            value = float_repr(value_float, precision_digits=scale)
        if self.company_dependent:
            return value_float
        return value

    def convert_to_cache(self, value, record, validate=True):
        # apply rounding here, otherwise value in cache may be wrong!
        value = float(value or 0.0)
        digits = self.get_digits(record.env)
        return float_round(value, precision_digits=digits[1]) if digits else value

    def convert_to_record(self, value, record):
        return value or 0.0

    def convert_to_export(self, value, record):
        if value or value == 0.0:
            return value
        return ''

    round = staticmethod(float_round)
    is_zero = staticmethod(float_is_zero)
    compare = staticmethod(float_compare)


class Monetary(Field[float]):
    """ Encapsulates a :class:`float` expressed in a given
    :class:`res_currency<odoo.addons.base.models.res_currency.Currency>`.

    The decimal precision and currency symbol are taken from the ``currency_field`` attribute.

    :param str currency_field: name of the :class:`Many2one` field
        holding the :class:`res_currency <odoo.addons.base.models.res_currency.Currency>`
        this monetary field is expressed in (default: `\'currency_id\'`)
    """
    type = 'monetary'
    write_sequence = 10
    _column_type = ('numeric', 'numeric')

    currency_field = None
    aggregator = 'sum'

    def __init__(self, string: str | Sentinel = SENTINEL, currency_field: str | Sentinel = SENTINEL, **kwargs):
        super(Monetary, self).__init__(string=string, currency_field=currency_field, **kwargs)

    def _description_currency_field(self, env):
        return self.get_currency_field(env[self.model_name])

    def get_currency_field(self, model):
        """ Return the name of the currency field. """
        return self.currency_field or (
            'currency_id' if 'currency_id' in model._fields else
            'x_currency_id' if 'x_currency_id' in model._fields else
            None
        )

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        assert self.get_currency_field(model) in model._fields, \
            "Field %s with unknown currency_field %r" % (self, self.get_currency_field(model))

    def setup_related(self, model):
        super().setup_related(model)
        if self.inherited:
            self.currency_field = self.related_field.get_currency_field(model.env[self.related_field.model_name])
        assert self.get_currency_field(model) in model._fields, \
            "Field %s with unknown currency_field %r" % (self, self.get_currency_field(model))

    def convert_to_column_insert(self, value, record, values=None, validate=True):
        # retrieve currency from values or record
        currency_field_name = self.get_currency_field(record)
        currency_field = record._fields[currency_field_name]
        if values and currency_field_name in values:
            dummy = record.new({currency_field_name: values[currency_field_name]})
            currency = dummy[currency_field_name]
        elif values and currency_field.related and currency_field.related.split('.')[0] in values:
            related_field_name = currency_field.related.split('.')[0]
            dummy = record.new({related_field_name: values[related_field_name]})
            currency = dummy[currency_field_name]
        else:
            # Note: this is wrong if 'record' is several records with different
            # currencies, which is functional nonsense and should not happen
            # BEWARE: do not prefetch other fields, because 'value' may be in
            # cache, and would be overridden by the value read from database!
            currency = record[:1].with_context(prefetch_fields=False)[currency_field_name]
            currency = currency.with_env(record.env)

        value = float(value or 0.0)
        if currency:
            return float_repr(currency.round(value), currency.decimal_places)
        return value

    def convert_to_cache(self, value, record, validate=True):
        # cache format: float
        value = float(value or 0.0)
        if value and validate:
            # FIXME @rco-odoo: currency may not be already initialized if it is
            # a function or related field!
            # BEWARE: do not prefetch other fields, because 'value' may be in
            # cache, and would be overridden by the value read from database!
            currency_field = self.get_currency_field(record)
            currency = record.sudo().with_context(prefetch_fields=False)[currency_field]
            if len(currency) > 1:
                raise ValueError("Got multiple currencies while assigning values of monetary field %s" % str(self))
            elif currency:
                value = currency.with_env(record.env).round(value)
        return value

    def convert_to_record(self, value, record):
        return value or 0.0

    def convert_to_read(self, value, record, use_display_name=True):
        return value

    def convert_to_write(self, value, record):
        return value

    def convert_to_export(self, value, record):
        if value or value == 0.0:
            return value
        return ''
