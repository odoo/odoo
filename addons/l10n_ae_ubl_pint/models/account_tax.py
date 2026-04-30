from odoo import api, fields, models

AE_EXEMPTION_REASON_CODES = [
    ('DL8.46.1', 'Certain financial services'),
    ('DL8.46.2', 'Supply of residential units (lease or sale)'),
    ('DL8.46.3', 'Bare land'),
    ('DL8.46.4', 'Local passenger transport'),
]

# The UNCL5305 codes PINT AE aligns, https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/Aligned-TaxCategoryCodes/
AE_TAX_CATEGORY_CODES = ['S', 'E', 'O', 'AE', 'Z', 'N']


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ubl_cii_tax_category_code = fields.Selection(
        selection_add=[('N', 'N - Standard rate additional VAT')],
        ondelete={'N': 'cascade'},
    )
    ubl_cii_tax_exemption_reason_code = fields.Selection(
        selection_add=AE_EXEMPTION_REASON_CODES,
        ondelete={code: 'cascade' for code, label in AE_EXEMPTION_REASON_CODES},
    )

    @api.depends('country_code')
    def _compute_ubl_cii_available_tax_category_codes(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_available_tax_category_codes()
        for tax in self.filtered(lambda t: t.country_code == 'AE'):
            tax.ubl_cii_available_tax_category_codes = AE_TAX_CATEGORY_CODES

    @api.depends('country_code')
    def _compute_ubl_cii_available_tax_exemption_reason_codes(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_available_tax_exemption_reason_codes()
        for tax in self.filtered(lambda t: t.country_code == 'AE'):
            tax.ubl_cii_available_tax_exemption_reason_codes = [code for code, label in AE_EXEMPTION_REASON_CODES]
