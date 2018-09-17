# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.multi
    def _send_order_confirmation_mail(self):
        # send order confirmation mail when payment done through the ecommerce
        confirmation_template = self.env['ir.config_parameter'].sudo().get_param('website_sale.ecommerce_confirmation_template', False)
        transcation = self.get_last_transaction()
        if transcation and confirmation_template:
            for order in transcation.sale_order_ids:
                self.env['mail.template'].browse(int(confirmation_template)).with_context(transaction=transcation, has_carrier=hasattr(order, 'carrier_id'), access_url=order._get_share_url(), is_confirmation_email=True).send_mail(order.id, notif_layout='mail.mail_notification_light')

    @api.multi
    def _set_transaction_pending(self):
        # Override of '_set_transaction_pending' in the 'payment' module
        # to sent the confirmation mail automatically.
        super(PaymentTransaction, self)._set_transaction_pending()
        self._send_order_confirmation_mail()

    @api.multi
    def _set_transaction_authorized(self):
        # Override of '_set_transaction_authorized' in the 'payment' module
        # to sent the confirmation mail automatically.
        super(PaymentTransaction, self)._set_transaction_authorized()
        self._send_order_confirmation_mail()

    @api.multi
    def _reconcile_after_transaction_done(self):
        # Override of '_set_transaction_done' in the 'payment' module
        # to sent the confirmation mail automatically.
        res = super(PaymentTransaction, self)._reconcile_after_transaction_done()
        self._send_order_confirmation_mail()
        return res
