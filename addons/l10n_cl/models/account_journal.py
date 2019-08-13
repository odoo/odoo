# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_cl_sequence_ids = fields.Many2many('ir.sequence', relation='l10n_cl_journal_sequence_rel', column1='journal_id',
                                            column2='sequence_id', string='Sequences')
    l10n_cl_share_sequences = fields.Boolean(
        'Unified Book',
        help='Use same sequence for documents with the same letter')

    def create_document_sequences(self):
        self.ensure_one()
        if self.company_id.country_id != self.env.ref('base.cl'):
            return True
        if not self.type == 'sale' or not self.l10n_latam_use_documents:
            return False

        if self.l10n_cl_share_sequences:
            return False

        internal_types = ['invoice', 'debit_note', 'credit_note']
        domain = [
            ('country_id.code', '=', 'CL'),
            ('internal_type', 'in', internal_types),
            ('active', '=', True)
        ]

        documents = self.env['l10n_latam.document.type'].search(domain)
        for document in documents:
            sequence = self.env['ir.sequence'].create(document.get_document_sequence_vals(self))
            self.update({'l10n_cl_sequence_ids': [(4, {sequence.id})]})
        return True

    @api.model
    def create(self, values):
        """ Create Document sequences after create the journal """
        res = super().create(values)
        res.create_document_sequences()
        return res

    def write(self, values):
        """ Update Document sequences after update journal """
        to_check = {'type', 'l10n_cl_share_sequences', 'l10n_latam_use_documents'}
        res = super().write(values)
        if to_check.intersection(set(values.keys())):
            for rec in self:
                rec.create_document_sequences()
        return res



