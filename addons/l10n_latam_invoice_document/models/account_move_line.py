# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        # Skip the computation of the field `l10n_latam_document_type_id` at the module installation
        # See `_auto_init` in `l10n_latam_invoice_document/models/account_move.py` for more information
        related='move_id.l10n_latam_document_type_id', bypass_search_access=True, store=True, index='btree_not_null', init_column=lambda model: None)
    l10n_latam_use_documents = fields.Boolean(related='move_id.l10n_latam_use_documents')
