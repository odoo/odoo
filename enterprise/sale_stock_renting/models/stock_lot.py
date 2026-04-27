# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression

class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    def _get_available_lots(self, product, location=None):
        """Get available lots for product in location.

        :param product.product product:
        :param stock.location location:
        """
        quant_domain = [
            ('product_id', '=', product.id),
            ('lot_id', '!=', False),
            ('location_id.usage', '=', 'internal')
        ]
        if location:
            quant_domain = expression.AND([quant_domain, [
                '|',
                ('location_id', '=', location.id),
                ('location_id', 'child_of', location.id)
            ]])

        return self.env['stock.quant'].search(quant_domain).lot_id

    @api.model
    def _get_lots_in_rent(self, product):
        """Company_wise"""
        return self._get_available_lots(product, self.env.company.rental_loc_id)
