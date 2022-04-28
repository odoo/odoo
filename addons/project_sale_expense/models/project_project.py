# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models


class Project(models.Model):
    _inherit = 'project.project'

    def _get_expenses_profitability_items(self, with_action=True):
        if not self.analytic_account_id:
            return {}
        can_see_expense = with_action and self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        expenses_read_group = self.env['hr.expense'].sudo()._read_group(
            [
                ('analytic_distribution_stored_char', '=ilike', f'%"{self.analytic_account_id.id}":%'),
                ('is_refused', '=', False),
                ('state', 'in', ['approved', 'done']),
            ],
            ['sale_order_id', 'product_id', 'ids:array_agg(id)', 'untaxed_amount'],
            ['sale_order_id', 'product_id'],
            lazy=False,
        )
        if not expenses_read_group:
            return {}
        expenses_per_so_id = {}
        expense_ids = []
        amount_billed = 0.0
        for res in expenses_read_group:
            so_id = res['sale_order_id'] and res['sale_order_id'][0]
            product_id = res['product_id'] and res['product_id'][0]
            expenses_per_so_id.setdefault(so_id, {})[product_id] = res['ids']
            if can_see_expense:
                expense_ids.extend(res['ids'])
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
        section_id = 'expenses'
        sequence = self._get_profitability_sequence_per_invoice_type()[section_id]
        expense_data = {
            'costs': {
                'id': section_id,
                'sequence': sequence,
                'billed': -amount_billed,
                'to_bill': 0.0,
            },
        }
        if reinvoice_expense_ids:
            expense_data['revenues'] = {
                'id': section_id,
                'sequence': sequence,
                'invoiced': total_amount_expense_invoiced,
                'to_invoice': total_amount_expense_to_invoice,
            }
        if can_see_expense:
            def get_action(res_ids):
                args = [section_id, [('id', 'in', res_ids)]]
                if len(res_ids) == 1:
                    args.append(res_ids[0])
                return {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}

            if reinvoice_expense_ids:
                expense_data['revenues']['action'] = get_action(reinvoice_expense_ids)
            if expense_ids:
                expense_data['costs']['action'] = get_action(expense_ids)
        return expense_data
