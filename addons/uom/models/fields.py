# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from operator import attrgetter

from odoo import fields
from odoo.tools import float_repr, float_round


class Measure(fields.Field):
    """ The rounding and decimal places are taken from the attribute

    :param str uom_field: name of the field holding the unit of measure
        this Measure field is expressed in (default: `\'uom_id\'`)
    """
    type = 'measure'
    column_type = ('numeric', 'numeric')
    column_cast_from = ('float8',)

    uom_field = None
    group_operator = 'sum'

    def __init__(self, string=fields.Default, uom_field=fields.Default, **kwargs):
        super().__init__(string=string, uom_field=uom_field, **kwargs)

    _description_uom_field = property(attrgetter('uom_field'))

    def _setup_uom_field(self, model):
        if not self.uom_field:
            # pick a default, trying in order: 'uom_id', 'x_uom_id'
            if 'uom_id' in model._fields:
                self.uom_field = 'uom_id'
            elif 'x_uom_id' in model._fields:
                self.uom_field = 'x_uom_id'
        assert self.uom_field in model._fields, \
            "Field %s with unknown uom_field %r" % (self, self.uom_field)

    def _setup_regular_full(self, model):
        super()._setup_regular_full(model)
        self._setup_uom_field(model)

    def _setup_related_full(self, model):
        super()._setup_related_full(model)
        if self.inherited:
            self.uom_field = self.related_field.uom_field
        self._setup_uom_field(model)

    def convert_to_column(self, value, record, values=None, validate=True):
        # retrieve unit of measure from values or record
        if values and self.uom_field in values:
            field = record._fields[self.uom_field]
            uom = field.convert_to_cache(values[self.uom_field], record, validate)
            uom = field.convert_to_record(uom, record)
        else:
            # Note: this is wrong if 'record' is several records with different
            # uom, which is functional nonsense and should not happen
            uom = record[:1][self.uom_field]

        value = float(value or 0.0)
        if uom:
            measure = float_round(value, precision_rounding=uom.rounding, rounding_method='HALF-UP')
            return float_repr(measure, uom.decimal_places)
        return value

    def convert_to_cache(self, value, record, validate=True):
        # cache format: float
        value = float(value or 0.0)
        if value and validate:
            # FIXME @rco-odoo: uom may not be already initialized if it is
            # a function or related field!
            uom = record.sudo()[self.uom_field]
            if len(uom) > 1:
                raise ValueError("Got multiple units of measure while assigning values of Measure field %s" % str(self))
            elif uom:
                value = float_round(value, precision_rounding=uom.rounding, rounding_method='HALF-UP')
        return value

    def convert_to_record(self, value, record):
        return value or 0.0

    def convert_to_read(self, value, record, use_name_get=True):
        return value

    def convert_to_write(self, value, record):
        return value

fields.Measure = Measure
