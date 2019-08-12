# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_district = fields.Many2one(
        'l10n_pe.res.city.district', string='District',
        help='Districts are part of a province or city.')

    def l10n_pe_get_customer_vat(self):
        """Based on current vat validation and implementation, the following
        logic set the code associated and its vat without prefix
        chat on its vat field.
          0 - Non-Domiciled Tax Document without RUC
        * 1 - National Identity Document (DNI, Spanish acronym)
        * 4 - Alien Registration Card
        * 6 - Single Taxpayer Registration (RUC, Spanish acronym)
        * 7 - Passport
        * A - Diplomatic Identity Card
        * B - Identity document of the country of residence
        * C - Tax Identification Number - TIN
        * D - Identification Number - IN
        * E - Andean Immigration Card (TAM, Spanish acronym)

        this represent the catalog no. 6 of SUNAT (1)
        http://cpe.sunat.gob.pe/sites/default/files/inline-files/anexoV-340-2017.pdf
        (*) types are supported in odoo core module base_vat
        """
        self.ensure_one()
        if not self.vat:
            return {"vat_number": '00000000', "vat_code": '1'}
        return {"vat_number": self.vat,
                "vat_code": (self.l10n_latam_identification_type_id
                             .l10n_pe_vat_code)}

    @api.constrains('vat', 'l10n_pe_latam_identification_type_id')
    def check_vat(self):
        """Method to validate all the document types of VAT in Peru."""
        partners_without_vat = self.filtered(
            lambda partner: not (partner.l10n_latam_identification_type_id
                                 .is_vat))

        for partner in partners_without_vat:
            vat_code = (partner.l10n_latam_identification_type_id
                        .l10n_pe_vat_code)
            vat = partner.vat
            # Verify Peruvian DNI
            if vat_code == '1':
                if self.check_dni(vat):
                    continue
                raise ValidationError(
                    _("The DNI is incorrect. \n - Lenght must be 8 or 9. \n"
                      " - Needs to be an integer. \n - The last digit must be"
                      " valid."))
            elif vat_code == '7':
                # Verify Peruvian Passport
                # https://epbs.migraciones.gob.pe/sistema-de-bloqueo/resources/images/passport.png
                if len(vat) > 12:
                    raise ValidationError(
                        _("The correct lenght of the Passport is under 12."))
                if bool(re.fullmatch(r'PERU[0-9]{5,6}', vat, re.IGNORECASE)):
                    continue
                raise ValidationError(
                    _("The standard of the Peruvian Passport is 'PERUXXXXX' or"
                      "'PERUXXXXXX'. The X represent a numeric value."))
            elif vat_code == '4':
                # Verify Alien Registration Card
                # http://cpe.sunat.gob.pe/sites/default/files/inline-files/Copia%20de%20AjustesValidacionesCPEv20190624_1.xlsx
                if len(vat) < 13:
                    continue
                raise ValidationError(_("The correct lenght of the Alien "
                                        "Registration Card is under 13."))
            else:
                # Verify the following types of VAT:
                # - Diplomatic Identify Card
                # - Identity document of the country of residence
                # - Tax Identification Number - TIN
                # - IdentificationNumber - IN,
                # - Andean Immigration Card (TAM, Spanish acronym)
                # http://cpe.sunat.gob.pe/sites/default/files/inline-files/Copia%20de%20AjustesValidacionesCPEv20190624_1.xlsx
                if len(vat) < 16:
                    continue
                raise ValidationError(
                    _("The correct lenght of the '%s' document is under 16.")
                    % partner.l10n_latam_identification_type_id.name)
        return super(ResPartner, self - partners_without_vat).check_vat()

    def check_dni(self, vat):
        """Verifying the DNI, and also calculating the possible check digits
        for it.
        https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/pe/cui.py
        """

        if len(vat) not in (8, 9) and not isinstance(vat, int):
            return False
        # Checking possible check digits.
        weights = (3, 2, 7, 6, 5, 4, 3, 2)
        digit = sum(w * int(n) for w, n in zip(weights, vat)) % 11
        return vat[-1] in '65432110987'[digit] + 'KJIHGFEDCBA'[digit]
