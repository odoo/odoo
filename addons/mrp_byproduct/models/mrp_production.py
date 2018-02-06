# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.tools import float_round


class MrpProduction(models.Model):
    _description = 'Production'
    _inherit = 'mrp.production'

    def _create_byproduct_move(self, sub_product):
        Move = self.env['stock.move']
        for production in self:
            source = production.product_id.property_stock_production.id
            product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty - production.qty_produced, production.bom_id.product_uom_id)
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
                'operation_id': sub_product.operation_id.id,
                'production_id': production.id,
                'origin': production.name,
                'unit_factor': qty1 / (production.product_qty - production.qty_produced),
                'subproduct_id': sub_product.id
            }
            move = Move.create(data)
            move._action_confirm()

    @api.multi
    def _generate_moves(self):
        """ Generates moves and work orders
        @return: Newly generated picking Id.
        """
        res = super(MrpProduction, self)._generate_moves()
        for production in self.filtered(lambda production: production.bom_id):
            for sub_product in production.bom_id.sub_products:
                production._create_byproduct_move(sub_product)
        return res


class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"
    _inherit = "mrp.product.produce"

    @api.multi
    def check_finished_move_lots(self):
        """ Handle by product tracked """
        by_product_moves = self.production_id.move_finished_ids.filtered(lambda m: m.product_id != self.product_id and m.product_id.tracking != 'none' and m.state not in ('done', 'cancel'))
        for by_product_move in by_product_moves:
            rounding = by_product_move.product_uom.rounding
            quantity = float_round(self.product_qty * by_product_move.unit_factor, precision_rounding=rounding)
            values = {
                'move_id': by_product_move.id,
                'product_id': by_product_move.product_id.id,
                'production_id': self.production_id.id,
                'product_uom_id': by_product_move.product_uom.id,
                'location_id': by_product_move.location_id.id,
                'location_dest_id': by_product_move.location_dest_id.id,
            }
            if by_product_move.product_id.tracking == 'lot':
                values.update({
                    'product_uom_qty': quantity,
                    'qty_done': quantity,
                })
                self.env['stock.move.line'].create(values)
            else:
                values.update({
                    'product_uom_qty': 1.0,
                    'qty_done': 1.0,
                })
                for i in range(0, int(quantity)):
                    self.env['stock.move.line'].create(values)
        return super(MrpProductProduce, self).check_finished_move_lots()
