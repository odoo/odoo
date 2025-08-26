# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_document_type_id = fields.Many2one(
        related='move_id.l10n_latam_document_type_id', auto_join=True, store=True, index='btree_not_null')

    def _get_fields_to_skip_compute_on_init(self):
        fields_to_skip_compute = super()._get_fields_to_skip_compute_on_init()
        fields_to_skip_compute.update([
            'l10n_latam_document_type_id',
        ])
        return fields_to_skip_compute
