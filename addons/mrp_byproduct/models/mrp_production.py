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
        picking_id = super(MrpProduction, self)._generate_moves()
        for production in self.filtered(lambda p: p.bom_id):
            source = production.product_id.property_stock_production
            for sub_product in production.bom_id.subproduct_ids:
                product_uom_factor = 1 #TODO:production.product_uom_id._compute_qty(production.product_qty, production.bom_id.product_uom_id.id)
                qty1 = sub_product.product_qty
                if sub_product.subproduct_type == 'variable' and production.product_qty:
                    qty1 *= product_uom_factor / (production.bom_id.product_qty or 1.0)
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
                    'subproduct_id': sub_product.id
                }

                StockMove.create(data).action_confirm()
        return picking_id

    def _get_subproduct_factor(self, move=None):
        """Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but with
            the module mrp_byproduct installed it can differ for byproducts having type 'variable'.
        :param move_id: ID of the stock move that needs to be produced. Identify the product to produce.
        :return: The factor to apply to the quantity that we should produce for the given production order and stock move.
        """
        self.ensure_one()
        sub_product = self.env['mrp.subproduct'].search([('product_id', '=', move.product_id.id), (
            'bom_id', '=', self.bom_id.id), ('subproduct_type', '=', 'variable')], limit=1)
        if sub_product.bom_id.product_qty:
            subproduct_factor = sub_product.product_qty / sub_product.bom_id.product_qty
            return subproduct_factor
        return super(MrpProduction, self)._get_subproduct_factor(move)