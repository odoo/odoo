# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        """Override of `sale` to archive guest contacts."""
        confirmed_orders = super()._check_amount_and_confirm_order()
        confirmed_orders.filtered('website_id')._archive_partner_if_no_user()
