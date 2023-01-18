# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.sql import column_exists, create_column


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _auto_init(self):
        # Skip the computation of the field `l10n_latam_document_type_id` at the module installation
        # See `_auto_init` in `l10n_latam_invoice_document/models/account_move.py` for more information
        if not column_exists(self.env.cr, "account_move_line", "l10n_latam_document_type_id"):
            create_column(self.env.cr, "account_move_line", "l10n_latam_document_type_id", "int4")
        return super()._auto_init()

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id', auto_join=True, store=True, index='btree_not_null')
    # TODO check if better to hange this field or create new one. By using the same field we avoid the need of changing
    # follow up view and journal item views
    move_name = fields.Char(
        compute='_compute_move_name', store=True, related=False,
        index='btree',
    )

    @api.depends('move_id.l10n_latam_full_document_number', 'move_id.name')
    def _compute_move_name(self):
        for rec in self:
            rec.move_name = rec.move_id.l10n_latam_full_document_number or rec.move_id.name
