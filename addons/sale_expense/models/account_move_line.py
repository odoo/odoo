# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _sale_can_be_reinvoice(self):
        """ determine if the generated analytic line should be reinvoiced or not.
            For Expense flow, if the product has a 'reinvoice policy' and a Sales Order is set on the expense, then we will reinvoice the AAL
        """
        self.ensure_one()
        if self.expense_id:  # expense flow is different from vendor bill reinvoice flow
            return self.expense_id.product_id.expense_policy in {'sales_price', 'cost'} and self.expense_id.sale_order_id
        return super()._sale_can_be_reinvoice()

    def _get_so_mapping_from_expense(self):
        mapping_from_expense = {}
        for move_line in self.filtered(lambda move_line: move_line.expense_id):
            mapping_from_expense[move_line.id] = move_line.expense_id.sale_order_id or None
        return mapping_from_expense

    def _sale_determine_order(self):
        """ For move lines created from expense, we override the normal behavior.
        """
        mapping_from_invoice = super()._sale_determine_order()
        mapping_from_invoice.update(self._get_so_mapping_from_expense())
        return mapping_from_invoice

    def _sale_prepare_sale_line_values(self, order, price):
        # Add expense quantity to sales order line and update the sales order price because it will be charged to the customer in the end.
        res = super()._sale_prepare_sale_line_values(order, price)
        if self.expense_id:
            res['name'] = self.name
            res['product_uom_qty'] = self.expense_id.quantity
        return res

    def _sale_create_reinvoice_sale_line(self):
        expensed_lines = self.filtered('expense_id')
        res = super(AccountMoveLine, self - expensed_lines)._sale_create_reinvoice_sale_line()
        res.update(super(AccountMoveLine, expensed_lines.with_context({'force_split_lines': True}))._sale_create_reinvoice_sale_line())
        return res
