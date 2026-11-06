# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.controllers import payment as account_payment


class PaymentPortal(account_payment.PaymentPortal):

    def _get_payment_options_context(self, *args, **kwargs):
        """Override of `payment` to make the provider filtering website-aware."""
        # Routes without `website=True` (e.g., the transaction routes) have the website in `host_id`
        website_id = self.env.website.id or self.env.context.get('host_id')
        return {**super()._get_payment_options_context(*args, **kwargs), 'website_id': website_id}
