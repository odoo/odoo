# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        """Make the VAT/NIF optional for small Spanish e-commerce orders.

        On Spanish e-commerce, ``l10n_es`` forces the VAT/NIF to be mandatory
        for every Spanish billing address. However, orders whose total is below
        the ``l10n_es_ecommerce.simplified_invoice_limit`` may be invoiced with a
        simplified invoice, which does not require the customer's VAT. For those
        orders we relax the requirement; at or above the limit the VAT stays
        mandatory (handled by the ``super`` call).
        """
        field_names = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)

        # ``l10n_es`` only adds 'vat' when both the company and the selected
        # billing country are Spain. There is nothing to relax otherwise.
        if 'vat' not in field_names:
            return field_names
        if self.env.company.country_code != 'ES' or country_sudo.code != 'ES':
            return field_names

        # The order is forwarded through the address-submit flow as a kwarg. The
        # dynamic "country changed" refresh route doesn't pass it, so fall back
        # to the current website cart.
        order_sudo = kwargs.get('order_sudo')
        if not order_sudo:
            # Can't determine the amount: keep VAT mandatory (safer default).
            return field_names

        threshold_amount = self.env['ir.config_parameter'].sudo().get_float(
            'l10n_es_ecommerce.simplified_invoice_limit', 400.0,
        )
        if order_sudo.amount_total < threshold_amount:
            # Below the limit a simplified invoice is enough -> VAT optional.
            field_names.discard('vat')

        return field_names
