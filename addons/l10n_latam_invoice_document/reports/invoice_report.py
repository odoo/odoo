from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    l10n_latam_document_type_id = fields.Many2one(
        comodel_name="l10n_latam.document.type",
        string="Document Type",
        index=True,
    )
    _depends = {
        "account.move": ["l10n_latam_document_type_id"],
    }

    def _select(self) -> SQL:
        return SQL(
            "%s, move.l10n_latam_document_type_id as l10n_latam_document_type_id",
            super()._select(),
        )
