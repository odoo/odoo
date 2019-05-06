# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountJournalDocumentType(models.Model):

    _name = 'l10n_latam.journal.mapping'
    _description = "Latam Document Mapping"
    _rec_name = 'document_type_id'
    _order = 'document_type_id'

    document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        'Document Type',
        required=True,
        ondelete='restrict',
        auto_join=True,
        index=True,
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Entry Sequence',
        ondelete='restrict',
        help="This field contains the information related to the numbering of "
        "the documents entries of this document type."
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        required=True,
        ondelete='cascade',
        auto_join=True,
    )
    next_number = fields.Integer(
        related='sequence_id.number_next_actual'
    )
