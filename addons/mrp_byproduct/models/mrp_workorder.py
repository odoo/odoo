# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def _post_sub_lots_used(self):
        super(MrpWorkorder, self)._post_sub_lots_used()
        for sub_product in self.production_id.bom_id.sub_products:
            quantity = self.qty_producing * sub_product.product_qty
            production_move = self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id == sub_product.product_id.id) and (x.state not in ('done', 'cancel')))
            if production_move.product_id.tracking != 'none':
                move_lot = production_move.move_lot_ids.filtered(lambda x: x.lot_id.id == self.final_lot_id.id and x.product_id.id == sub_product.product_id.id)
                if move_lot:
                    move_lot.quantity += quantity
                else:
                    move_lot.create({'move_id': production_move.id,
                                     'lot_id': self.final_lot_id.id,
                                     'quantity': self.qty_producing,
                                     'quantity_done': self.qty_producing,
                                     'workorder_id': self.id,
                                     'product_id': sub_product.product_id.id,
                                     })
            else:
                production_move.quantity_done += quantity
