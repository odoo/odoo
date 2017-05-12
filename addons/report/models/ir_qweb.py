# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.base.ir.ir_qweb import unicodifier


class IrQwebFieldBarcode(models.AbstractModel):
    """ ``barcode`` widget rendering, inserts a data:uri-using image tag in the
    document. May be overridden by e.g. the website module to generate links
    instead.
    """
    _name = 'ir.qweb.field.barcode'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options=None):
        barcode_type = options.get('type', 'Code128')
        barcode = self.env['report'].barcode(
            barcode_type,
            value,
            **dict((key, value) for key, value in options.items() if key in ['width', 'height', 'humanreadable']))
        return unicodifier('<img src="data:%s;base64,%s">' % ('png', barcode.encode('base64')))

    @api.model
    def from_html(self, model, field, element):
        return None
