# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_subcontract_return()

    def _get_value_from_account_move(self, quantity):
        valuation_data = super()._get_value_from_account_move(quantity)
        last_subcontract_done_receipt = self.move_dest_ids.filtered(
            lambda m: m.state == 'done' and m.is_subcontract and m.purchase_line_id
        ).sorted('create_date', reverse=True)[:1]
        if not self.production_id or not last_subcontract_done_receipt:
            return valuation_data

        bill_data = last_subcontract_done_receipt.with_context(valuation_without_extra=True)._get_value_from_account_move(quantity)
        po_data = last_subcontract_done_receipt._get_value_from_quotation(quantity - bill_data['quantity'])
        if not bill_data['value'] and not po_data['value']:
            return valuation_data

        old_extra = self.production_id.extra_cost
        new_extra_cost = (bill_data['value'] + po_data['value']) / quantity

        # Add only the subcontracting cost difference, leaving the quantity for production valuation.
        value = (new_extra_cost - old_extra) * quantity
        valued_quantity = 0
        if self.product_id.cost_method == 'standard':
            value += self.product_id.standard_price * quantity
            valued_quantity = quantity
        return {
            'value': value,
            'quantity': valued_quantity,
            'description': self.env._('%(value)s for %(quantity)s %(unit)s from %(production)s',
                value=self.company_currency_id.format(value), quantity=quantity, unit=self.product_id.uom_id.name,
                production=self.production_id.display_name),
        }
