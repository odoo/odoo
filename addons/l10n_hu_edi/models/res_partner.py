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
