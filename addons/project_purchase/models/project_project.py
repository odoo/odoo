# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _, _lt
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    purchase_orders_count = fields.Integer('# Purchase Orders', compute='_compute_purchase_orders_count', groups='purchase.group_purchase_user')

    @api.depends('analytic_account_id')
    def _compute_purchase_orders_count(self):
        data = self.env['purchase.order.line']._read_group(
            [('analytic_distribution', 'in', self.analytic_account_id.ids)],
            ['analytic_distribution'],
            ['__count'],
        )
        data = {int(account_id): order_count for account_id, order_count in data}
        for project in self:
            project.purchase_orders_count = data.get(project.analytic_account_id.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    def action_open_project_purchase_orders(self):
        purchase_orders = self.env['purchase.order.line'].search(
            [('analytic_distribution', 'in', self.analytic_account_id.ids)]
        ).order_id
        action_window = {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', purchase_orders.ids)],
            'context': {
                'project_id': self.id,
            }
        }
        if len(purchase_orders) == 1:
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = purchase_orders.id
        return action_window

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name == 'purchase_order':
            action = {
                'name': _('Purchase Order Items'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order.line',
                'views': [[False, 'tree'], [False, 'form']],
                'domain': domain,
                'context': {
                    'create': False,
                    'edit': False,
                },
            }
            if res_id:
                action['res_id'] = res_id
                if 'views' in action:
                    action['views'] = [
                        (view_id, view_type)
                        for view_id, view_type in action['views']
                        if view_type == 'form'
                    ] or [False, 'form']
                action['view_mode'] = 'form'
            return action
        return super().action_profitability_items(section_name, domain, res_id)

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.env.user.has_group('purchase.group_purchase_user'):
            self_sudo = self.sudo()
            buttons.append({
                'icon': 'credit-card',
                'text': _lt('Purchase Orders'),
                'number': self_sudo.purchase_orders_count,
                'action_type': 'object',
                'action': 'action_open_project_purchase_orders',
                'show': self_sudo.purchase_orders_count > 0,
                'sequence': 36,
            })
        return buttons

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            ['|', ('move_line_id', '=', False), ('move_line_id.purchase_line_id', '=', False)],
        ])

    def _add_purchase_items(self, profitability_items, with_action=True):
        return False

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['purchase_order'] = _lt('Purchase Orders')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['purchase_order'] = 10
        return sequence_per_invoice_type

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        if self.analytic_account_id:
            invoice_lines = self.env['account.move.line'].sudo().search_fetch([
                ('parent_state', 'in', ['draft', 'posted']),
                ('analytic_distribution', 'in', self.analytic_account_id.ids),
                ('purchase_line_id', '!=', False),
            ], ['parent_state', 'currency_id', 'price_unit', 'quantity', 'analytic_distribution'])
            purchase_order_line_invoice_line_ids = self._get_already_included_profitability_invoice_line_ids()
            with_action = with_action and (
                self.env.user.has_group('purchase.group_purchase_user')
                or self.env.user.has_group('account.group_account_invoice')
                or self.env.user.has_group('account.group_account_readonly')
            )
            if invoice_lines:
                amount_invoiced = amount_to_invoice = 0.0
                purchase_order_line_invoice_line_ids.extend(invoice_lines.ids)
                for line in invoice_lines:
                    price_unit = line.currency_id._convert(line.price_unit, self.currency_id, self.company_id)
                    analytic_contribution = sum(
                        percentage for ids, percentage in line.analytic_distribution.items()
                        if str(self.analytic_account_id.id) in ids.split(',')
                    ) / 100.
                    cost = price_unit * line.quantity * analytic_contribution if line.quantity > 0 else 0.0
                    if line.parent_state == 'posted':
                        amount_invoiced -= cost
                    else:
                        amount_to_invoice -= cost
                costs = profitability_items['costs']
                section_id = 'purchase_order'
                purchase_order_costs = {'id': section_id, 'sequence': self._get_profitability_sequence_per_invoice_type()[section_id], 'billed': amount_invoiced, 'to_bill': amount_to_invoice}
                if with_action:
                    args = [section_id, [('id', 'in', invoice_lines.purchase_line_id.ids)]]
                    if len(invoice_lines.purchase_line_id) == 1:
                        args.append(invoice_lines.purchase_line_id.id)
                    action = {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}
                    purchase_order_costs['action'] = action
                costs['data'].append(purchase_order_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice
            domain = [
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('parent_state', 'in', ['draft', 'posted']),
                ('price_subtotal', '>', 0),
                ('id', 'not in', purchase_order_line_invoice_line_ids),
            ]
            self._get_costs_items_from_purchase(domain, profitability_items, with_action=with_action)
        return profitability_items
