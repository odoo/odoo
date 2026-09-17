# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_ecommerce_is_eu_oss_installed(self):
        """Whether the EU One Stop Shop (OSS) module is installed."""
        return 'l10n_eu_oss' in self.env['ir.module.module']._installed()

    def _l10n_es_ecommerce_identification_required(self, country_sudo, state_sudo, order_sudo=None):
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
        if not order_sudo or order_sudo.amount_total > self.env.company.l10n_es_simplified_invoice_limit:
            return True
        if not country_sudo:
            return False
        if country_sudo.code == 'ES':
            return bool(state_sudo) and state_sudo.code in ('GC', 'TF', 'CE', 'ME')
        if 'EU' not in (country_sudo.country_group_codes or ''):
            return True
        return self._l10n_es_ecommerce_is_eu_oss_installed()

    def _check_billing_address(self, **kwargs):
        """Require an identifier (VAT or an alternative ES ID document)"""
        if not super()._check_billing_address(**kwargs):
            return False
        if self.env.company.country_code != 'ES':
            return True
        if not self._l10n_es_ecommerce_identification_required(
            self.country_id, self.state_id, order_sudo=kwargs.get('order_sudo')
        ):
            return True
        return self._l10n_es_has_identification()
