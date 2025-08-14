# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools
from odoo.osv import expression


class PosOrder(models.Model):
    _inherit = 'pos.order'

    use_self_order_online_payment = fields.Boolean(compute='_compute_use_self_order_online_payment', store=True, readonly=True)

    @api.depends('config_id.self_order_online_payment_method_id')
    def _compute_use_self_order_online_payment(self):
        for order in self:
            order.use_self_order_online_payment = bool(order.config_id.self_order_online_payment_method_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'use_self_order_online_payment' not in vals or vals['use_self_order_online_payment']:
                session = self.env['pos.session'].browse(vals['session_id'])
                config = session.config_id
                vals['use_self_order_online_payment'] = bool(config.self_order_online_payment_method_id)
        return super().create(vals_list)

    def write(self, vals):
        # Because use_self_order_online_payment is not intended to be changed manually,
        # avoid to raise an error.
        if 'use_self_order_online_payment' not in vals:
            return super().write(vals)

        can_change_self_order_domain = [('state', '=', 'draft')]
        if vals['use_self_order_online_payment']:
            can_change_self_order_domain = expression.AND([can_change_self_order_domain, [('config_id.self_order_online_payment_method_id', '!=', False)]])

        can_change_self_order_orders = self.filtered_domain(can_change_self_order_domain)
        cannot_change_self_order_orders = self - can_change_self_order_orders

        res = True
        if can_change_self_order_orders:
            res = super(PosOrder, can_change_self_order_orders).write(vals) and res
        if cannot_change_self_order_orders:
            clean_vals = vals.copy()
            clean_vals.pop('use_self_order_online_payment', None)
            res = super(PosOrder, cannot_change_self_order_orders).write(clean_vals) and res

        return res

    @api.depends('use_self_order_online_payment', 'config_id.self_order_online_payment_method_id', 'config_id.payment_method_ids')
    def _compute_online_payment_method_id(self):
        for order in self:
            if order.use_self_order_online_payment:
                # It is expected to use the self order online payment method.
                # If for any reason it is not defined, then the online payment
                # of the order is set to null to make the problem noticeable.
                order.online_payment_method_id = order.config_id.self_order_online_payment_method_id
            else:
                super(PosOrder, order)._compute_online_payment_method_id()

    def get_and_set_online_payments_data(self, next_online_payment_amount=False):
        res = super().get_and_set_online_payments_data(next_online_payment_amount)
        if 'paid_order' not in res and not res.get('deleted', False) and not isinstance(next_online_payment_amount, bool):
            # This method is only called in the POS frontend flow, not self order.
            # If the next online payment is 0, then the online payment of the frontend
            # flow is cancelled, and the default flow is self order if it is configured.
            self.use_self_order_online_payment = tools.float_is_zero(next_online_payment_amount, precision_rounding=self.currency_id.rounding) and self.config_id.self_order_online_payment_method_id
        return res

    def _send_notification_online_payment_status(self, status):
        self.config_id.notify_synchronisation(self.config_id.current_session_id.id, 0)
        self.config_id._notify("ONLINE_PAYMENT_STATUS", {
            'status': status,  # progress, success, fail
            'data': {
                'pos.order': self.read(self._load_pos_self_data_fields(self.config_id.id), load=False),
                'pos.payment': self.payment_ids.read(self.payment_ids._load_pos_self_data_fields(self.config_id.id), load=False),
            }
        })
