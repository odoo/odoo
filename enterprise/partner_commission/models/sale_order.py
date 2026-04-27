# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    referrer_id = fields.Many2one('res.partner', 'Referrer', domain=[('grade_id', '!=', False)], tracking=True)
    commission_plan_frozen = fields.Boolean(
        'Freeze Plan', tracking=True,
        help="Whether the commission plan is frozen. When checked, the commission plan won't automatically be updated according to the partner level.")
    commission_plan_id = fields.Many2one(
        'commission.plan',
        'Commission Plan',
        compute='_compute_commission_plan',
        inverse='_set_commission_plan',
        store=True,
        tracking=True,
        help="Takes precedence over the Referrer's commission plan.")
    commission = fields.Monetary(string='Referrer Commission', compute='_compute_commission')

    @api.depends('referrer_id', 'commission_plan_id', 'sale_order_template_id', 'pricelist_id', 'order_line.price_subtotal')
    def _compute_commission(self):
        self.commission = 0
        for so in self:
            if not so.referrer_id or not so.commission_plan_id:
                so.commission = 0
            else:
                comm_by_rule = defaultdict(float)
                template = so.sale_order_template_id
                template_id = template.id if template else None
                for line in so.order_line:
                    rule = so.commission_plan_id._match_rules(line.product_id, template_id, so.pricelist_id.id)
                    if rule:
                        commission = so.currency_id.round(line.price_subtotal * rule.rate / 100.0)
                        comm_by_rule[rule] += commission

                # cap by rule
                for r, amount in comm_by_rule.items():
                    if r.is_capped:
                        amount = min(amount, r.max_commission)
                        comm_by_rule[r] = amount

                so.commission = sum(comm_by_rule.values())

    @api.depends('commission_plan_frozen', 'partner_id', 'referrer_id', 'referrer_id.commission_plan_id')
    def _compute_commission_plan(self):
        for so in self:
            if not so.is_subscription and so.state in ['draft', 'sent']:
                so.commission_plan_id = so.referrer_id.commission_plan_id
            elif so.is_subscription and not so.commission_plan_frozen:
                so.commission_plan_id = so.referrer_id.commission_plan_id

    def _set_commission_plan(self):
        updated_plan_sale_order = self.filtered(lambda order: not order.commission_plan_frozen and order.referrer_id and order.referrer_id.commission_plan_id != order.commission_plan_id)
        updated_plan_sale_order.commission_plan_frozen = True

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.referrer_id:
            invoice_vals.update({
                'referrer_id': self.referrer_id.id,
            })
        return invoice_vals

    def _prepare_upsell_renew_order_values(self, subscription_state):
        self.ensure_one()
        values = super()._prepare_upsell_renew_order_values(subscription_state)
        if self.referrer_id:
            values.update({
                'referrer_id': self.referrer_id.id,
                'commission_plan_id': self.commission_plan_id.id,
                'commission_plan_frozen': self.referrer_id.commission_plan_id != self.commission_plan_id,
            })
        return values
