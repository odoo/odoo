# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()

    def _get_value_from_account_move(self, quantity, at_date=None):
        valuation_data = super()._get_value_from_account_move(quantity, at_date=at_date)
        last_subcontract_done_receipt = self.move_dest_ids.filtered(
            lambda m: m.state == 'done' and m.is_subcontract and m.purchase_line_id
        )
        if not self.production_id or not last_subcontract_done_receipt:
            return valuation_data

        bill_data = last_subcontract_done_receipt._get_value_from_account_move(quantity)
        po_data = last_subcontract_done_receipt._get_value_from_quotation(quantity - bill_data['quantity'])
        if not bill_data['value'] and not po_data['value']:
            return valuation_data

        old_extra = self.production_id.extra_cost
        new_extra_cost = (bill_data['value'] + po_data['value']) / quantity

        # Recompute finished_move price based on quotation and invoice
        value = (self.price_unit - old_extra + new_extra_cost) * self.quantity
        return {
            'value': value,
            'quantity': quantity,
            'description': self.env._('%(value)s for %(quantity)s %(unit)s from %(production)s',
                value=self.company_currency_id.format(self.value), quantity=quantity, unit=self.product_id.uom_id.name,
                production=self.production_id.display_name),
        }
