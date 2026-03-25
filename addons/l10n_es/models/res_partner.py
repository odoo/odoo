import re

from odoo import models
from odoo.tools.business_data import split_vat


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_is_foreign(self):
        self.ensure_one()

        return self.country_id.code not in ('ES', False) or (self.vat or '').upper().startswith(("ESN", "N"))

    def _l10n_es_freelancer(self):
        self.ensure_one()
        if not self.has_vat:
            return False

        vat = split_vat(self.vat, default_country_code='ES')[1]

        return re.fullmatch(r"(\d{8}[TRWAGMYFPDXBNJZSQVHLCKE]|[XYZ]\d{7}[TRWAGMYFPDXBNJZSQVHLCKE]|E\d{7}[A-J0-9])", vat) or False

    def _l10n_es_edi_get_partner_info(self):
        """ Used in SII and Veri*factu"""
        self.ensure_one()
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        partner_info = {}
        IDOtro_ID = self.has_vat and self.vat or 'NO_DISPONIBLE'

        if (not self.country_id or self.country_id.code == 'ES') and self.has_vat:
            # ES partner with VAT.
            partner_info['NIF'] = self.vat.removeprefix('ES')
            if self.env.context.get('error_1117'):
                partner_info['IDOtro'] = {'IDType': '07', 'ID': IDOtro_ID}

        elif self.country_id.code in eu_country_codes and self.has_vat:
            # European partner.
            partner_info['IDOtro'] = {'IDType': '02', 'ID': IDOtro_ID}
        else:
            partner_info['IDOtro'] = {'ID': IDOtro_ID}
            if self.has_vat:
                partner_info['IDOtro']['IDType'] = '04'
            else:
                partner_info['IDOtro']['IDType'] = '06'
            if self.country_id:
                partner_info['IDOtro']['CodigoPais'] = self.country_id.code
        return partner_info

    def _compute_is_company(self):
        """
        Determines if the Spanish VAT corresponds to a legal entity (CIF format):
        CIF = 1 letter + 7 digits + checksum (digit or letter) (e.g., A1234567Y)
        """
        super()._compute_is_company()
        for partner in self:
            country_code, _ = split_vat(partner.vat)
            if partner.commercial_partner_id == partner and (country_code == 'ES' or (not country_code and partner.country_code == 'ES')):
                partner.is_company = not partner._l10n_es_freelancer()
