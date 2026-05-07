from odoo import models

import re

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_is_foreign(self):
        self.ensure_one()

        return self.country_id.code not in ('ES', False) or (self.vat or '').startswith("ESN")

    def _l10n_es_edi_get_partner_info(self):
        """ Used in SII and Veri*factu"""
        self.ensure_one()
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        partner_info = {}
        IDOtro_ID = self.vat or 'NO_DISPONIBLE'

        if (not self.country_id or self.country_id.code == 'ES') and self.vat:
            # ES partner with VAT.
            partner_info['NIF'] = self.vat.removeprefix('ES')
            if self.env.context.get('error_1117'):
                partner_info['IDOtro'] = {'IDType': '07', 'ID': IDOtro_ID}

        elif self.country_id.code in eu_country_codes and self.vat:
            # European partner.
            partner_info['IDOtro'] = {'IDType': '02', 'ID': IDOtro_ID}
        else:
            partner_info['IDOtro'] = {'ID': IDOtro_ID}
            if self.vat:
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
        for partner in self.filtered('vat'):
            vat_number, country_code = partner._run_vat_checks(partner.country_id, partner.vat, validation=False)
            if vat_number.startswith('ES'):
                vat_number = vat_number[2:]
            if country_code in ('ES', ''):
                if len(vat_number) == 9\
                    and vat_number[0].upper() in 'ABCDEFGHJNPQRSUVW'\
                    and vat_number[1:-1].isdigit():
                    partner.is_company = True
                elif re.fullmatch(r"(\d{8}[TRWAGMYFPDXBNJZSQVHLCKE]|[XYZ]\d{7}[TRWAGMYFPDXBNJZSQVHLCKE]|E\d{7}[A-J0-9])", vat_number) or False:
                    partner.is_company = False

