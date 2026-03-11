# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        """Override of `sale` to archive guest contacts."""
        super()._post_process()
        if self.env["ir.config_parameter"].sudo().get_bool("sale.automatic_invoice"):
            self.sale_order_ids.filtered("website_id")._archive_partner_if_no_user()
