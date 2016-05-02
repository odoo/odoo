# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Production(models.Model):
    _description = 'Production'
    _inherit = 'mrp.production'

    @api.multi
    def action_confirm(self):
        """ Confirms production order and calculates quantity based on subproduct_type.
        @return: Newly generated picking Id.
        """
        Move = self.env['stock.move']
        picking_id = super(Production, self).action_confirm()
        UoM = self.env['product.uom']
        for production in self:
            if not production.bom_id:
                continue
            source = production.product_id.property_stock_production.id
            for sub_product in production.bom_id.sub_products:
                product_uom_factor = UoM._compute_qty_obj(production.product_uom, production.product_qty, production.bom_id.product_uom)
                qty1 = sub_product.product_qty
                if sub_product.subproduct_type == 'variable' and production.product_qty:
                    qty1 *= product_uom_factor / (production.bom_id.product_qty or 1.0)
                data = {
                    'name': 'PROD:%s' % production.name,
                    'date': production.date_planned,
                    'product_id': sub_product.product_id.id,
                    'product_uom_qty': qty1,
                    'product_uom': sub_product.product_uom.id,
                    'location_id': source,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'production_id': production.id,
                    'origin': production.name,
                    'subproduct_id': sub_product.id
                }
                move = Move.create(data)
                move.action_confirm()
        return picking_id

    @api.model
    def _get_subproduct_factor(self, move):
        """Compute the factor to compute the quantity of products to produce. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but with
            the module mrp_byproduct installed it can differ for byproducts having type 'variable'.
        :param move: Record set of stock move that needs to be produced, identify the product to produce.
        :return: The factor to apply to the quantity that we should produce for the given production order and stock move.
        """
        subproduct_record = move.subproduct_id
        if subproduct_record.subproduct_type == 'variable':
            if subproduct_record.bom_id.product_qty:
                subproduct_factor = subproduct_record.product_qty / subproduct_record.bom_id.product_qty
                return subproduct_factor
        return super(Production, self)._get_subproduct_factor(move)

    @api.model
    def _calculate_produce_line_qty(self, move, quantity):
        """ Compute the quantity and remainig quantity of products to produce.
        :param move: stock.move record that needs to be produced, identify the product to produce.
        :param quantity: quantity to produce, in the uom of the production order.
        :return: The quantity and remaining quantity of product produce.
        """
        if move.subproduct_id.subproduct_type == 'variable':
            subproduct_factor = self._get_subproduct_factor(move)
            # Needed when producing more than maximum quantity
            qty = min(subproduct_factor * quantity, move.product_qty)
            remaining_qty = subproduct_factor * quantity - qty
            return qty, remaining_qty
        elif move.subproduct_id.subproduct_type == 'fixed':
            return move.product_qty, 0
        # no subproduct
        return super(Production, self)._calculate_produce_line_qty(move, quantity)
