# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Production(models.Model):
    _description = 'Production'
    _inherit = 'mrp.production'


    @api.multi
    def _generate_moves(self):
        """ Generates moves and work orders
        @return: Newly generated picking Id.
        """
        # TDE FIXME: was action_confirm ?? -> refactored
        Move = self.env['stock.move']
        res = super(Production, self)._generate_moves()
        for production in self.filtered(lambda production: production.bom_id):
            source = production.product_id.property_stock_production.id
            for sub_product in production.bom_id.sub_products:
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                qty1 = sub_product.product_qty
                qty1 *= product_uom_factor / production.bom_id.product_qty
                data = {
                    'name': 'PROD:%s' % production.name,
                    'date': production.date_planned_start,
                    'product_id': sub_product.product_id.id,
                    'product_uom_qty': qty1,
                    'product_uom': sub_product.product_uom_id.id,
                    'location_id': source,
                    'location_dest_id': production.location_dest_id.id,
                    'production_id': production.id,
                    'origin': production.name,
                    'unit_factor': qty1 / production.product_qty,
                    'subproduct_id': sub_product.id
                }
                move = Move.create(data)
                move.action_confirm()
        return res
