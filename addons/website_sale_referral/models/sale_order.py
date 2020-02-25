# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from ast import literal_eval


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'referral.abstract']

    referred_email = fields.Char(related='partner_id.email')
    referred_name = fields.Char(related='partner_id.name')
    referred_company_name = fields.Char(compute='_compute_referred_company_name', store=False)

    @api.depends('partner_id', 'partner_id.company_id', 'partner_id.company_id.name')
    def _compute_referred_company_name(self):
        for order in self:
            order.referred_company_name = order.partner_id.company_id.name if order.partner_id.company_id else ''

    def _is_fully_paid(self):
        self.ensure_one()
        if self.invoice_status != 'invoiced':
            return False
        amount_paid = 0.0
        for inv in self.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.payment_state == 'paid'):
            amount_paid += inv.currency_id._convert(inv.amount_total, self.currency_id, self.company_id, self.date_order)
        return not self.currency_id.compare_amounts(self.amount_total, amount_paid)

    def get_referral_statuses(self, utm_source_id, referred_email=None):
        sales_orders = self.find_others(utm_source_id, referred_email)

        result = {}
        for so in sales_orders:
            state = so._get_state_for_referral()
            if(so.partner_id.email not in result or self.STATES_PRIORITY[state] > self.STATES_PRIORITY[result[so.partner_id.email]]):
                result[so.partner_id.email] = state

        if referred_email:
            return result.get(referred_email, None)
        return result

    def _get_state_for_referral(self):
        self.ensure_one()
        if self.state == 'draft':
            return 'new'
        if self._is_fully_paid():
            return 'done'
        if self.state == 'cancel':
            return 'cancel'
        return 'in_progress'

    def write(self, vals):
        if not self.env.user.has_group('website_crm_referral.group_lead_referral') and \
                any([elem in vals for elem in ['state', 'invoice_status', 'amount_total']]):
            orders = list(filter(lambda o: o.campaign_id == self.env.ref('website_sale_referral.utm_campaign_referral') and not o.deserve_reward, self))
            old_states = {order: order._get_referral_statuses(self.source_id, self.partner_id.email) for order in orders}
            r = super().write(vals)
            new_states = {order: order._get_referral_statuses(self.source_id, self.partner_id.email) for order in orders}
            for order in orders:
                order._check_and_apply_progress(old_states[order], new_states[order])
            return r
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        campaign = self.env.ref('website_sale_referral.utm_campaign_referral')
        referral_orders = res.filtered(lambda order: order.campaign_id == campaign)
        if referral_orders:
            vals = {}
            if self.env.company.salesperson_id:
                vals['user_id'] = self.env.company.salesperson_id.id
            if self.env.company.salesteam_id:
                vals['team_id'] = self.env.company.salesteam_id.id
            referral_orders.write(vals)
        return res
