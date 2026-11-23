# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_kr.tools.partner_identifiers import KR_ADDITIONAL_IDENTIFIERS_METADATA

L10N_KR_ISSUANCE_TYPES = [
    ('tax_invoice', "Tax Invoice"),
    ('tax_exempt_invoice', "Tax-exempt Invoice"),
    ('card_payment', "Credit Card"),
    ('cash_receipt', "Cash Receipt"),
    ('other', "Other"),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_kr_default_issuance_type = fields.Selection(
        selection=L10N_KR_ISSUANCE_TYPES,
        string="Proof of Issuance",
        help="Default proof of issuance to use when this partner is set on a sales order or invoice.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            'l10n_kr_default_issuance_type',
        ]

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **KR_ADDITIONAL_IDENTIFIERS_METADATA}
