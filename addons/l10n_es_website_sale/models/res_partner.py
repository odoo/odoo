# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_ecommerce_is_eu_oss_installed(self):
        """Whether the EU One Stop Shop (OSS) module is installed."""
        return 'l10n_eu_oss' in self.env['ir.module.module']._installed()

    def _l10n_es_ecommerce_identification_required(self, country_sudo, state_sudo):
        """Whether the customer must provide identification (VAT or an alternative ES ID
        document) to check out: outside the EU, or inside Spain's VAT-territory (TAI)
        exclusions -- the Canary Islands, Ceuta and Melilla are part of Spain but are
        extra-comunitario for VAT purposes, so a full invoice (never simplified) is always
        issued to them too, and it needs an identifier to report (see l10n_es's invoice-type
        and SII/TicketBAI IDOtro computations).

        When the EU One Stop Shop (``l10n_eu_oss``) is installed, sales to other EU member
        states are taxed in the customer's country, so identification is required for them
        as well.
        """
        if not country_sudo:
            return False
        if country_sudo.code == 'ES':
            return bool(state_sudo) and state_sudo.code in ('GC', 'TF', 'CE', 'ME')
        if 'EU' not in (country_sudo.country_group_codes or ''):
            return True
        return self._l10n_es_ecommerce_is_eu_oss_installed()

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        """Make the VAT/NIF mandatory or optional on Spanish e-commerce orders
        based on the order amount, regardless of the customer's billing country.

        Orders whose total is at or below ``l10n_es_simplified_invoice_limit``
        (the company field already provided by l10n_es) may be invoiced with a
        simplified invoice, which does not require the customer's VAT. Above the
        limit -- or when the amount can't be determined -- VAT stays mandatory.
        """
        field_names = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)

        if self.env.company.country_code != 'ES':
            return field_names

        # The order is forwarded through the address-submit flow as a kwarg. The
        # dynamic "country changed" refresh route doesn't pass it, so fall back
        # to the current website cart.
        order_sudo = kwargs.get('order_sudo')
        if not order_sudo:
            # Can't determine the amount: keep VAT mandatory (safer default).
            field_names.add('vat')
            return field_names

        # Same threshold/comparison l10n_es uses to flag an invoice as
        # simplified (amount <= limit), so checkout and invoicing stay aligned.
        threshold_amount = self.env.company.l10n_es_simplified_invoice_limit
        if order_sudo.amount_total <= threshold_amount:
            field_names.discard('vat')
        else:
            field_names.add('vat')

        return field_names
