# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    @api.multi
    def _generate_moves(self):
        """
            Generates moves and work orders
        """
        StockMove = self.env['stock.move']
        uom_obj = self.env['product.uom']
        picking_id = super(MrpProduction, self)._generate_moves()
        for production in self.filtered(lambda p: p.bom_id):
            source = production.product_id.property_stock_production
            for sub_product in production.bom_id.subproduct_ids:
                import pdb; pdb.set_trace()
                product_uom_factor = uom_obj._compute_qty(production.product_uom_id.id, production.product_qty, production.bom_id.product_uom_id.id)
                #TODO:production.product_uom_id._compute_qty(production.product_qty, production.bom_id.product_uom_id.id)
                qty1 = sub_product.product_qty
                qty1 *= product_uom_factor / production.bom_id.product_qty
                data = {
                    'name': _('PROD:%s') % production.name,
                    'date': production.date_planned,
                    'product_id': sub_product.product_id.id,
                    'product_uom_qty': qty1,
                    'product_uom': sub_product.product_uom_id.id,
                    'location_id': source.id,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'production_id': production.id,
                    'origin': production.name,
                    'unit_factor': qty1 / production.product_qty,
                    'subproduct_id': sub_product.id
                }

                StockMove.create(data).action_confirm()
        return picking_id