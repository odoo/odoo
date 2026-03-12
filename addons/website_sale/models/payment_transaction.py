# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _send_invoice(self):
        """Override of `sale` to archive guest contacts."""
        super()._send_invoice()
        self.sale_order_ids.filtered(
            lambda so: so.state == "sale" and so.website_id
        )._archive_partner_if_no_user()
