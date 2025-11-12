# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        """Override of ``payment`` to confirm orders paid on delivery and trigger a picking
        creation."""
        pod_txs = self._filtered_pending_delivery_payment()
        pod_txs.sale_order_ids.filtered(lambda so: so.state == "draft").with_context(
            send_email=True
        ).action_confirm()
        super()._post_process()

    def _should_create_payment(self):
        """Override of ``account_payment`` to defer the creation of payments for transactions paid
        on delivery.

        The payment is created once settled in PoS.
        """
        return super()._should_create_payment() and not bool(
            self._filtered_pending_delivery_payment()
        )

    def _filtered_pending_delivery_payment(self):
        """Filter transactions waiting for a payment to be confirmed on delivery."""
        pay_on_delivery_codes = self.env["payment.method"]._get_pay_on_delivery_method_codes()
        return self.filtered_domain(
            Domain([
                ("payment_method_code", "in", pay_on_delivery_codes),
                ("state", "=", "pending"),
            ])
        )
