# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    purchase_order_count = fields.Integer("Purchase Order Count", compute='_compute_purchase_order_count')

    @api.depends('line_ids')
    def _compute_purchase_order_count(self):
        plan_column_names = self._get_all_plan_column_names()

        for account in self:
            account.purchase_order_count = self.env['purchase.order'].search_count(self._get_domains_for_po_search(plan_column_names, account.id))

    def action_view_purchase_orders(self):
        self.ensure_one()
        domains = self._get_domains_for_po_search(self._get_all_plan_column_names(), self.id)
        purchase_orders = self.env['purchase.order'].search(domains)
        result = {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "domain": [['id', 'in', purchase_orders.ids]],
            "name": _("Purchase Orders"),
            'view_mode': 'list,form',
        }
        if len(purchase_orders) == 1:
            result['view_mode'] = 'form'
            result['res_id'] = purchase_orders.id
        return result

    def _get_all_plan_column_names(self):
        return ['order_line.invoice_lines.analytic_line_ids.' + plan._column_name() for plan in self.env['account.analytic.plan'].search([])]

    def _get_domains_for_po_search(self, plan_column_names, account_id):
        domains = []
        if len(plan_column_names) > 0:
            domains.extend('|' for _ in range(len(plan_column_names) - 1))
            domains.extend((pcn, '=', account_id) for pcn in plan_column_names)
        return domains
