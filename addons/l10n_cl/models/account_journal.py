# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_cl_sequence_ids = fields.Many2many(
        'ir.sequence', 'l10n_cl_journal_sequence_rel', 'journal_id', 'sequence_id', string='Sequences (cl)',
        domain="[('l10n_latam_document_type_id', '!=', False)]")