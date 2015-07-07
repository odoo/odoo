# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import sets

from openerp import models

class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule, self)._get_type_selection())
        types.update([
            ('weight','Weighted Product'),
            ('price','Priced Product'),
            ('discount','Discounted Product'),
            ('client','Client'),
            ('cashier','Cashier')
        ])
        return list(types)
