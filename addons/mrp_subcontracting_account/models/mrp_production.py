# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _cal_price(self, consumed_moves):
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity > 0)
        # Take the price unit of the reception move
        last_done_receipt = finished_move.move_dest_ids.filtered(lambda m: m.state == 'done')[-1:]
        if last_done_receipt.is_subcontract:
            quantity = last_done_receipt.quantity
            bill_data = last_done_receipt._get_value_from_account_move(quantity)
            po_data = last_done_receipt._get_value_from_quotation(quantity - bill_data['quantity'])
            if not bill_data['value'] and not po_data['value']:
                self.extra_cost = last_done_receipt.price_unit
            else:
                self.extra_cost = (bill_data['value'] + po_data['value']) / quantity
        return super()._cal_price(consumed_moves=consumed_moves)
