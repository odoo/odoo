# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp import api


class product_product(osv.osv):
    _inherit = 'product.product'

    @api.onchange('type')
    def onchange_type_valuation(self):
        if self.type != 'product':
            self.valuation = 'manual_periodic'
        return {}
