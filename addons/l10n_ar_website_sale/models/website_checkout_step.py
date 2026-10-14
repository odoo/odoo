# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteCheckoutStep(models.Model):
    _inherit = 'website.checkout.step'

    def _get_billing_address_alert(self, order_sudo):
        partner_sudo = order_sudo.partner_invoice_id
        if (
            not partner_sudo.vat
            and not partner_sudo._get_additional_identifier('AR_DNI')
            and 'AR_DNI' in partner_sudo._get_mandatory_additional_identifiers(
                partner_sudo.country_id, order_sudo=order_sudo,
            )
        ):
            return self.env._("This order requires your identification number. Please provide it.")
        return super()._get_billing_address_alert(order_sudo)
