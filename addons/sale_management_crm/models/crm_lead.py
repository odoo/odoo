# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Orders", help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    quotation_count = fields.Integer(compute='_compute_sale_data', string="Number of Quotations")
    sale_order_count = fields.Integer(compute='_compute_sale_data', string="Number of Sales Orders")

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:
            total = 0.0
            quotation_cnt = 0
            sale_order_cnt = 0
            company_currency = lead.company_currency or self.env.company.currency_id
            orders = self._get_filtered_sale_order(lead.order_ids)
            for order in orders:
                if order.state in ('draft', 'sent'):
                    quotation_cnt += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    sale_order_cnt += 1
                    total += order.currency_id._convert(
                        order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today())
            lead.sale_amount_total = total
            lead.quotation_count = quotation_cnt
            lead.sale_order_count = sale_order_cnt

    def action_new_quotation(self):
        if self.env.context.get('is_sale_order'):
            action = self.env.ref("sale_management_crm.new_quotation_action").read()[0]
            action['context'] = self._get_quotation_action_context()
            return action
        return super().action_new_quotation()

    def action_view_sale_order(self):
        if self.env.context.get('order_status') == 'quotation':
            action_id = 'sale.action_quotations_with_onboarding'
            order_states = ('draft', 'sent')
        else:
            action_id = 'sale.action_orders'
            order_states = ('sale', 'done')
        action = self.env.ref(action_id).read()[0]
        orders = self._get_filtered_sale_order(self.mapped('order_ids'))
        action.update(self._get_base_view_order_action(states=order_states, sale_orders=orders))
        if action.get('res_id'):
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        return action
