# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models

import sets


class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule,self)._get_type_selection()) 
        types.update([
            ('weight','Weighted Product'),
            ('location','Location'),
            ('lot','Lot'),
            ('package','Package')
        ])
        return list(types)
