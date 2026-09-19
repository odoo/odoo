from odoo import fields, models
from odoo.db.schema import column_exists, create_column


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _auto_init(self):
        # Skip the computation of the field `l10n_latam_document_type_id` at the module installation
        # See `_auto_init` in `l10n_latam_invoice_document/models/account_move.py` for more information
        if not column_exists(
            self.env.cr, "account_move_line", "l10n_latam_document_type_id"
        ):
            create_column(
                self.env.cr, "account_move_line", "l10n_latam_document_type_id", "int4"
            )
        return super()._auto_init()

    l10n_latam_document_type_id = fields.Many2one(
        related="move_id.l10n_latam_document_type_id",
        bypass_search_access=True,
    )
    l10n_latam_use_documents = fields.Boolean(
        related="move_id.l10n_latam_use_documents"
    )
