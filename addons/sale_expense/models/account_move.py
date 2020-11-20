# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _sale_can_be_reinvoice(self):
        """ determine if the generated analytic line should be reinvoiced or not.
            For Expense flow, if the product has a 'reinvoice policy' and a Sales Order is set on the expense, then we will reinvoice the AAL
        """
        self.ensure_one()
        if self.expense_id:  # expense flow is different from vendor bill reinvoice flow
            return self.expense_id.product_id.expense_policy in ['sales_price', 'cost'] and self.expense_id.sale_order_id
        return super(AccountMoveLine, self)._sale_can_be_reinvoice()

    def _sale_determine_order(self):
        """ For move lines created from expense, we override the normal behavior.
            Note: if no SO but an AA is given on the expense, we will determine anyway the SO from the AA, using the same
            mecanism as in Vendor Bills.
        """
        mapping_from_invoice = super(AccountMoveLine, self)._sale_determine_order()

        mapping_from_expense = {}
        for move_line in self.filtered(lambda move_line: move_line.expense_id):
            mapping_from_expense[move_line.id] = move_line.expense_id.sale_order_id or None

        mapping_from_invoice.update(mapping_from_expense)
        return mapping_from_invoice

    def _sale_prepare_sale_line_values(self, order, price):
        # Add expense quantity to sales order line and update the sales order price because it will be charged to the customer in the end.
        self.ensure_one()
        res = super()._sale_prepare_sale_line_values(order, price)
        if self.expense_id:
            res.update({'product_uom_qty': self.expense_id.quantity})
        return res
