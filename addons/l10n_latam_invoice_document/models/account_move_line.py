# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id', auto_join=True, store=True, index='btree_not_null')
