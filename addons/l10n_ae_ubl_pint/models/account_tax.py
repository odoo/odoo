from odoo import fields, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import TAX_EXEMPTION_MAPPING

AE_EXEMPTION_REASON_CODES = [
    ('DL8.46.1', 'Certain financial services'),
    ('DL8.46.2', 'Supply of residential units (lease or sale)'),
    ('DL8.46.3', 'Bare land'),
    ('DL8.46.4', 'Local passenger transport'),
]

# _get_tax_exemption_reason builds the exported Reason text from this dict, not from the
# Selection field's own labels (selection_add alone doesn't feed it) - without this, AE's codes
# would export with a generic "Exempt from tax" text instead of their real FTA wording.
TAX_EXEMPTION_MAPPING.update(dict(AE_EXEMPTION_REASON_CODES))


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ubl_cii_tax_category_code = fields.Selection(
        selection_add=[('N', 'N - Margin scheme goods')],
        ondelete={'N': 'cascade'},
    )
    ubl_cii_tax_exemption_reason_code = fields.Selection(
        selection_add=AE_EXEMPTION_REASON_CODES,
        ondelete={code: 'cascade' for code, label in AE_EXEMPTION_REASON_CODES},
    )
    l10n_ae_available_exemption_reason_codes = fields.Json(compute='_compute_l10n_ae_available_exemption_reason_codes')

    def _compute_l10n_ae_available_exemption_reason_codes(self):
        for tax in self:
            tax.l10n_ae_available_exemption_reason_codes = [code for code, label in AE_EXEMPTION_REASON_CODES]
