# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Override of `payment` to confirm orders with on_site payment method to trigger a picking
         creation.
        """
        on_site_pending_txs = self.filtered(
            lambda tx: tx.provider_id.custom_mode == 'on_site' and tx.state == 'pending'
        )
        super(PaymentTransaction, self - on_site_pending_txs)._post_process()
        on_site_pending_txs.sale_order_ids.filtered(
            lambda so: so.state == 'draft'
        ).with_context(send_email=True).action_confirm()
