# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MeasureConverter(models.AbstractModel):
    _name = 'ir.qweb.field.measure'
    _description = 'Qweb Field Measure'
    _inherit = 'ir.qweb.field.float'

    @api.model
    def record_to_html(self, record, field_name, options):
        uom = record[record._fields[field_name].uom_field]
        options.pop('decimal_precision', None)
        options = dict(options, precision=uom.decimal_places)
        return super().record_to_html(record, field_name, options)
