# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
import re


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    internal_type = fields.Selection(
        selection_add=[
            ("purchase_liquidation", "Purchase Liquidation"),
            ("withhold", "Withhold"),
        ]
    )

    l10n_ec_check_format = fields.Boolean(
        string="Check Number Format EC", default=False
    )

    def _format_document_number(self, document_number):
        self.ensure_one()
        if self.country_id != self.env.ref("base.ec"):
            return super()._format_document_number(document_number)
        if not document_number:
            return False
        if self.l10n_ec_check_format:
            document_number = re.sub(r'\s+', "", document_number)  # remove any whitespace
            num_match = re.match(r'(\d{1,3})-(\d{1,3})-(\d{1,9})', document_number)
            if num_match:
                # Fill each number group with zeroes (3, 3 and 9 respectively)
                document_number = "-".join([n.zfill(3 if i < 2 else 9) for i, n in enumerate(num_match.groups())])
            else:
                raise UserError(_(
                    "Ecuadorian Document %s must be like 001-001-123456789",
                    self.display_name
                ))

        return document_number
