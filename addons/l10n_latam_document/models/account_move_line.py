# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id',
        readonly=True,
        auto_join=True,
        store=True,
        index=True,
    )
