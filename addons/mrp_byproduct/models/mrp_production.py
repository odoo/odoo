# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def action_confirm(self):
        StockMove = self.env['stock.move']
        picking_id = super(MrpProduction, self).action_confirm()
        for production in self.filtered(lambda p: p.bom_id):
            source_id = production.product_id.property_stock_production.id
            for sub_product in production.bom_id.sub_products_ids:
                product_uom_factor = production.product_uom._compute_qty(production.product_qty, production.bom_id.product_uom.id)
                qty1 = sub_product.product_qty
                if sub_product.subproduct_type == 'variable' and production.product_qty:
                    qty1 *= product_uom_factor / (production.bom_id.product_qty or 1.0)
                data = {
                    'name': _('PROD:%s') % production.name,
                    'date': production.date_planned,
                    'product_id': sub_product.product_id.id,
                    'product_uom_qty': qty1,
                    'product_uom': sub_product.product_uom_id.id,
                    'location_id': source_id,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'production_id': production.id
                }
                StockMove.create(data).action_confirm()
        return picking_id

    @api.multi
    def _get_subproduct_factor(self, move_id=None):
        """Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but with
            the module mrp_byproduct installed it can differ for byproducts having type 'variable'.
        :param move_id: ID of the stock move that needs to be produced. Identify the product to produce.
        :return: The factor to apply to the quantity that we should produce for the given production order and stock move.
        """
        self.ensure_one()
        move = self.env['stock.move'].browse(move_id)
        sub_product = self.env['mrp.subproduct'].search([('product_id', '=', move.product_id.id), (
            'bom_id', '=', self.bom_id.id), ('subproduct_type', '=', 'variable')], limit=1)
        if sub_product.bom_id.product_qty:
            subproduct_factor = sub_product.product_qty / sub_product.bom_id.product_qty
            return subproduct_factor
        return super(MrpProduction, self)._get_subproduct_factor(move_id)
