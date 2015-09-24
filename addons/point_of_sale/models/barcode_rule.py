# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import sets
from openerp import models
from openerp.tools.translate import _


class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule,self)._get_type_selection())
        types.update([
            ('weight', _('Weighted Product')),
            ('price', _('Priced Product')),
            ('discount', _('Discounted Product')),
            ('client', _('Client')),
            ('cashier', _('Cashier'))
        ])
        return list(types)
