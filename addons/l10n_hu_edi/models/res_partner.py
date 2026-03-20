# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_hu_group_vat = fields.Char(
        string='Group Tax ID',
        size=13,
        help="If this company belongs to a VAT group, indicate the group's VAT number here.",
        index=True,
    )

    def _compute_is_company(self):
        """
            A partner can be identified as a company in two ways:

            1. VAT follows the European format:
            - Starts with 'HU' and Followed by 8 digits
            Example: HU12345678

            2. VAT follows the Hungarian domestic format:
            - 8 digits - [2/4/5] - 2 digits
            Example: 12345678-2-43
        """
        l10n_hu_partners = self.filtered(lambda p: p.country_code == 'HU')
        for partner in l10n_hu_partners:
            if partner._is_vat_void(partner.vat):
                partner.is_company = False
                continue
            vat = (partner.vat).replace(' ', '').upper()
            partner.is_company = (vat.startswith('HU') and len(vat) == 10) \
                or bool(self._check_tin_hu_companies_re.fullmatch(vat)) or False

        super(ResPartner, self - l10n_hu_partners)._compute_is_company()

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            'l10n_hu_group_vat',
        ]

    @api.model
    def _run_vies_test(self, vat_number, default_country):
        """Convert back the hungarian format to EU format: 12345678-1-12 => HU12345678"""
        if default_country and default_country.code == 'HU' and not vat_number.startswith('HU'):
            vat_number = f'HU{vat_number[:8]}'
        return super()._run_vies_test(vat_number, default_country)
