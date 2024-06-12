# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


class PosOrder(models.Model):
    _inherit = 'pos.order'

    online_payment_method_id = fields.Many2one('pos.payment.method', compute="_compute_online_payment_method_id")
    next_online_payment_amount = fields.Float(string='Next online payment amount to pay', digits=0, required=False) # unlimited precision

    @api.depends('config_id.payment_method_ids')
    def _compute_online_payment_method_id(self):
        for order in self:
            order.online_payment_method_id = order.config_id._get_cashier_online_payment_method()

    def get_amount_unpaid(self):
        self.ensure_one()
        return self.currency_id.round(self._get_rounded_amount(self.amount_total) - self.amount_paid)

    def _clean_payment_lines(self):
        self.ensure_one()
        order_payments = self.env['pos.payment'].search(['&', ('pos_order_id', '=', self.id), ('online_account_payment_id', '=', False)])
        order_payments.unlink()

    def get_and_set_online_payments_data(self, next_online_payment_amount=False):
        """ Allows to update the amount to pay for the next online payment and
            get online payments already made and how much remains to be paid.
            If next_online_payment_amount is different than False, updates the
            next online payment amount, otherwise, the next online payment amount
            is unchanged.
            If next_online_payment_amount is 0 and the order has no successful
            online payment, is in draft state, is not a restaurant order and the
            pos.config has no trusted config, then the order is deleted from the
            database, because it was probably added for the online payment flow.
        """
        self.ensure_one()
        is_paid = self.state in ('paid', 'done', 'invoiced')
        if is_paid:
            return {
                'id': self.id,
                'paid_order': self._export_for_ui(self)
            }

        online_payments = self.sudo().env['pos.payment'].search_read(domain=['&', ('pos_order_id', '=', self.id), ('online_account_payment_id', '!=', False)], fields=['payment_method_id', 'amount'], load=False)
        return_data = {
            'id': self.id,
            'online_payments': online_payments,
            'amount_unpaid': self.get_amount_unpaid(),
        }
        if not isinstance(next_online_payment_amount, bool):
            if tools.float_is_zero(next_online_payment_amount, precision_rounding=self.currency_id.rounding) and len(online_payments) == 0 and self.state == 'draft' and not self.config_id.module_pos_restaurant and len(self.config_id.trusted_config_ids) == 0:
                self.sudo()._clean_payment_lines() # Needed to delete the order
                self.sudo().unlink()
                return_data['deleted'] = True
            elif self._check_next_online_payment_amount(next_online_payment_amount):
                self.next_online_payment_amount = next_online_payment_amount

        return return_data

    def _send_online_payments_notification_via_bus(self):
        self.ensure_one()
        # The bus communication is only protected by the name of the channel.
        # Therefore, no sensitive information is sent through it, only a
        # notification to invite the local browser to do a safe RPC to
        # the server to check the new state of the order.
        self.env['bus.bus']._sendone(self.session_id._get_bus_channel_name(), 'ONLINE_PAYMENTS_NOTIFICATION', {'id': self.id})

    def _check_next_online_payment_amount(self, amount):
        self.ensure_one()
        return tools.float_compare(amount, 0.0, precision_rounding=self.currency_id.rounding) >= 0 and tools.float_compare(amount, self.get_amount_unpaid(), precision_rounding=self.currency_id.rounding) <= 0

    def _get_checked_next_online_payment_amount(self):
        self.ensure_one()
        amount = self.next_online_payment_amount
        return amount if self._check_next_online_payment_amount(amount) else False
