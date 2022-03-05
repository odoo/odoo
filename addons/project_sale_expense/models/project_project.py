# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class Project(models.Model):
    _inherit = 'project.project'

    def _get_expenses_profitability_items(self):
        if not self.analytic_account_id:
            return {}
        expenses_read_group = self.env['hr.expense'].sudo()._read_group(
            [
                ('analytic_account_id', 'in', self.analytic_account_id.ids),
                ('is_refused', '=', False),
                ('state', 'in', ['approved', 'done']),
            ],
            ['sale_order_id', 'product_id', 'untaxed_amount'],
            ['sale_order_id', 'product_id'],
            lazy=False,
        )
        if not expenses_read_group:
            return {}
        expenses_per_so_id = {}
        amount_billed = 0.0
        for res in expenses_read_group:
            so_id = res['sale_order_id'] and res['sale_order_id'][0]
            product_id = res['product_id'] and res['product_id'][0]
            expenses_per_so_id.setdefault(so_id, {})[product_id] = res['ids']
            amount_billed += res['untaxed_amount']
        sol_read_group = self.env['sale.order.line'].sudo()._read_group(
            [
                ('order_id', 'in', list(expenses_per_so_id.keys())),
                ('is_expense', '=', True),
                ('state', 'in', ['sale', 'done']),
            ],
            ['order_id', 'product_id', 'untaxed_amount_to_invoice', 'untaxed_amount_invoiced'],
            ['order_id', 'product_id'],
            lazy=False)
        total_amount_expense_invoiced = total_amount_expense_to_invoice = 0.0
        reinvoice_expense_ids = []
        for res in sol_read_group:
            expense_data_per_product_id = expenses_per_so_id[res['order_id'][0]]
            product_id = res['product_id'][0]
            if product_id in expense_data_per_product_id:
                total_amount_expense_to_invoice += res['untaxed_amount_to_invoice']
                total_amount_expense_invoiced += res['untaxed_amount_invoiced']
                reinvoice_expense_ids += expense_data_per_product_id[product_id]
        expense_name = _('Expenses')
        section_id = 'expenses'
        expense_data = {
            'costs': {
                'id': section_id,
                'name': expense_name,
                'billed': -amount_billed,
                'to_bill': 0.0,
            },
        }
        if reinvoice_expense_ids:
            expense_data['revenues'] = {
                'id': section_id,
                'name': expense_name,
                'invoiced': total_amount_expense_invoiced,
                'to_invoice': total_amount_expense_to_invoice,
            }
        return expense_data
