# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_gt.tools.partner_identifiers import GT_ADDITIONAL_IDENTIFIERS_METADATA

VAT_WITHHOLDING_TYPES = [
    ('special_taxpayer', "Special Taxpayer"),
    ('exporter', "Exporter"),
    ('exporter_29_89', "Exporter Decree 29-89"),
    ('public_sector', "Public Sector"),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gt_isr_withholding_agent = fields.Boolean(
        string="ISR Retention Agent",
    )
    l10n_gt_vat_withholding_type = fields.Selection(
        selection=VAT_WITHHOLDING_TYPES,
        string="VAT Retention Type",
        help="Regime under which VAT is withheld. "
             "Leave empty if not a VAT retention agent.",
    )

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **GT_ADDITIONAL_IDENTIFIERS_METADATA}
