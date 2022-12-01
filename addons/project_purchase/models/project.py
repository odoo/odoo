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
        if not self.analytic_account_id:
            self.purchase_orders_count = 0
            return
        purchase_orders_data = self.env['purchase.order.line']._read_group([
            ('account_analytic_id', 'in', self.analytic_account_id.ids)
        ], ['account_analytic_id', 'order_id:count_distinct'], ['account_analytic_id'])
        mapped_data = dict([(data['account_analytic_id'][0], data['order_id']) for data in purchase_orders_data])
        for project in self:
            project.purchase_orders_count = mapped_data.get(project.analytic_account_id.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    def action_open_project_purchase_orders(self):
        purchase_orders = self.env['purchase.order'].search([
            ('order_line.account_analytic_id', '!=', False),
            ('order_line.account_analytic_id', 'in', self.analytic_account_id.ids)
        ])
        action_window = {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', purchase_orders.ids)],
            'context': {
                'create': False,
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
        if self.user_has_groups('purchase.group_purchase_user'):
            buttons.append({
                'icon': 'credit-card',
                'text': _lt('Purchase Orders'),
                'number': self.purchase_orders_count,
                'action_type': 'object',
                'action': 'action_open_project_purchase_orders',
                'show': self.purchase_orders_count > 0,
                'sequence': 36,
            })
        return buttons

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            ['|', ('move_id', '=', False), ('move_id.purchase_line_id', '=', False)],
        ])

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['purchase_order'] = _lt('Purchase Orders')
        labels['other_purchase_costs'] = _lt('Other Costs')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['purchase_order'] = 9
        sequence_per_invoice_type['other_purchase_costs'] = 10
        return sequence_per_invoice_type

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        if self.analytic_account_id:
            purchase_order_line_read = self.env['purchase.order.line'].sudo().search_read([
                ('account_analytic_id', 'in', self.analytic_account_id.ids),
                ('state', 'in', ['purchase', 'done']),
                '|',
                ('qty_invoiced', '>', 0),
                '|', ('qty_to_invoice', '>', 0), ('product_uom_qty', '>', 0),
            ], ['invoice_lines', 'qty_invoiced', 'qty_to_invoice', 'product_uom_qty', 'price_unit'])
            purchase_order_line_invoice_line_ids = []
            if purchase_order_line_read:
                amount_invoiced = amount_to_invoice = 0.0
                purchase_order_line_ids = []
                for pol_read in purchase_order_line_read:
                    purchase_order_line_invoice_line_ids.extend(pol_read['invoice_lines'])
                    price_unit = pol_read['price_unit']
                    amount_invoiced -= price_unit * pol_read['qty_invoiced'] if pol_read['qty_invoiced'] > 0 else 0.0
                    if pol_read['qty_to_invoice'] > 0:
                        amount_to_invoice -= price_unit * pol_read['qty_to_invoice']
                    else:
                        amount_to_invoice -= price_unit * (pol_read['product_uom_qty'] - pol_read['qty_invoiced'])
                    purchase_order_line_ids.append(pol_read['id'])
                costs = profitability_items['costs']
                section_id = 'purchase_order'
                purchase_order_costs = {'id': section_id, 'sequence': self._get_profitability_sequence_per_invoice_type()[section_id], 'billed': amount_invoiced, 'to_bill': amount_to_invoice}
                if with_action and purchase_order_line_ids and self.user_has_groups('purchase.group_purchase_user'):
                    action = {'name': 'action_profitability_items', 'type': 'object', 'section': section_id, 'domain': json.dumps([('id', 'in', purchase_order_line_ids)])}
                    if len(purchase_order_line_ids) == 1:
                        action['res_id'] = purchase_order_line_ids[0]
                    purchase_order_costs['action'] = action
                costs['data'].append(purchase_order_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice
            # calculate the cost of bills without a purchase order
            query = self.env['account.move.line'].sudo()._search([
                ('analytic_account_id', 'in', self.analytic_account_id.ids),
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('parent_state', 'in', ['draft', 'posted']),
                ('price_subtotal', '>', 0),
                ('id', 'not in', purchase_order_line_invoice_line_ids),
            ])
            # account_move_line__move_id is the alias of the joined table account_move in the query
            # we can use it, because of the "move_id.move_type" clause in the domain of the query, which generates the join
            # this is faster than a search_read followed by a browse on the move_id to retrieve the move_type of each account.move.line
            query_string, query_param = query.select('price_subtotal', 'parent_state', 'account_move_line__move_id.move_type')
            self._cr.execute(query_string, query_param)
            bills_move_line_read = self._cr.dictfetchall()
            if bills_move_line_read:
                amount_invoiced = amount_to_invoice = 0.0
                for moves_read in bills_move_line_read:
                    if moves_read['parent_state'] == 'draft':
                        if moves_read['move_type'] == 'in_invoice':
                            amount_to_invoice -= moves_read['price_subtotal']
                        else:  # moves_read['move_type'] == 'in_refund'
                            amount_to_invoice += moves_read['price_subtotal']
                    else:  # moves_read['parent_state'] == 'posted'
                        if moves_read['move_type'] == 'in_invoice':
                            amount_invoiced -= moves_read['price_subtotal']
                        else:  # moves_read['move_type'] == 'in_refund'
                            amount_invoiced += moves_read['price_subtotal']
                # don't display the section if the final values are both 0 (bill -> vendor credit)
                if amount_invoiced != 0 or amount_to_invoice != 0:
                    costs = profitability_items['costs']
                    section_id = 'other_purchase_costs'
                    bills_costs = {
                        'id': section_id,
                        'sequence': self._get_profitability_sequence_per_invoice_type()[section_id],
                        'billed': amount_invoiced,
                        'to_bill': amount_to_invoice,
                    }
                    costs['data'].append(bills_costs)
                    costs['total']['billed'] += amount_invoiced
                    costs['total']['to_bill'] += amount_to_invoice
        return profitability_items
