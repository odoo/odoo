from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_latam_document_type_id = fields.Many2one(
        related="move_id.l10n_latam_document_type_id",
        bypass_search_access=True,
    )
    l10n_latam_use_documents = fields.Boolean(
        related="move_id.l10n_latam_use_documents"
    )
