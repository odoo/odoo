# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Override of `payment` to confirm orders with the cash_on_delivery payment method and
        trigger a picking creation. """
        cod_pending_txs = self.filtered(
            lambda tx: tx.provider_id.custom_mode == 'cash_on_delivery' and tx.state == 'pending'
        )
        cod_pending_txs.sale_order_ids.filtered(
            lambda so: so.state == 'draft'
        ).with_context(send_email=True).action_confirm()
        super()._post_process()
