# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, _lt


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

    def _get_profitability_items(self):
        profitability_items = super()._get_profitability_items()
        if self.analytic_account_id:
            purchase_order_line_read = self.env['purchase.order.line'].sudo().search_read([
                ('account_analytic_id', 'in', self.analytic_account_id.ids),
                ('state', '!=', 'cancel'),
                '|', ('qty_invoiced', '>', 0), ('qty_to_invoice', '>', 0),
            ], ['qty_invoiced', 'qty_to_invoice', 'price_unit'])
            if purchase_order_line_read:
                amount_invoiced = amount_to_invoice = 0.0
                purchase_order_line_ids = []
                for pol_read in purchase_order_line_read:
                    price_unit = pol_read['price_unit']
                    amount_invoiced -= price_unit * pol_read['qty_invoiced'] if pol_read['qty_invoiced'] > 0 else 0.0
                    amount_to_invoice -= price_unit * pol_read['qty_to_invoice'] if pol_read['qty_to_invoice'] > 0 else 0.0
                    purchase_order_line_ids.append(pol_read['id'])
                costs = profitability_items['costs']
                section_id = 'purchase_order'
                purchase_order_costs = {'id': section_id, 'name': _('Purchase Order'), 'billed': amount_invoiced, 'to_bill': amount_to_invoice}
                costs['data'].append(purchase_order_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice
        return profitability_items
