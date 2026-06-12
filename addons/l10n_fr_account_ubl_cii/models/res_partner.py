import re

from odoo import fields, models

siren_siret_re = re.compile(r'^(\d{9}|\d{14})$')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_21_fr', "France E-Invoicing (UBL 2.1)")])

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------
    def _l10n_fr_is_b2c(self):
        self.ensure_one()
        return self.vat == '/' or not self.vat

    def _l10n_fr_get_siren(self):
        self.ensure_one()
        id_type, id_value = self._l10n_fr_get_base_identifier()
        if id_type in ('siren', 'siret'):
            return id_value[:9]
        return False

    def _l10n_fr_get_base_identifier(self):
        self.ensure_one()
        siret = self.siret or (self.company_registry if self.company_registry and siren_siret_re.match(self.company_registry) else '')
        siren = siret[:9]
        if len(siret) == 9:
            return 'siren', siren
        elif len(siret) == 14:
            return 'siret', siret
        return None, None

    def _get_suggested_pdp_identifier(self):
        self.ensure_one()
        # We suggest the SIREN (even if the SIRET is filled in).
        # "Everyone" will probably have registered the SIREN on annuaire. (Even if they have a SIRET.)
        return self._l10n_fr_get_siren()

    def _get_peppol_endpoint_value(self, country_code, field):
        self.ensure_one()
        if country_code == 'FR' and field == 'peppol_endpoint':
            return self._get_suggested_pdp_identifier()
        return super()._get_peppol_endpoint_value(country_code, field)

    def _build_error_peppol_endpoint(self, eas, endpoint):
        # Extend 'account_edi_ubl_cii' for '0225' endpoint
        if eas != '0225':
            return super()._build_error_peppol_endpoint(eas, endpoint)
        if not self.env["res.company"]._check_pdp_identifier(endpoint):
            return self.env._("The Peppol endpoint is not valid. The expected format is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or SIREN_SuffixeAdressage")

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_21_fr':
            return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_21_fr'] = {'countries': ['FR'], 'on_peppol': False}
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'FR' and not self._l10n_fr_is_b2c():
            return 'ubl_21_fr'
        return super()._get_suggested_invoice_edi_format()
