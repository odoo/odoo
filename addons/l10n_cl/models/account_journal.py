# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_cl_sequence_ids = fields.Many2many(
        'ir.sequence', 'l10n_cl_journal_sequence_rel', 'journal_id', 'sequence_id', string='Sequences',
        domain="[('l10n_latam_document_type_id', '!=', False)]")

    def create_document_sequences(self):
        self.ensure_one()
        if (self.company_id.country_id != self.env.ref('base.cl')) or ((self.env['ir.sequence'].search(
                [('l10n_latam_document_type_id', '!=', False)]) and not self.env.context.get(
                'manual_creation', False))) or not self.type == 'sale' or not self.l10n_latam_use_documents:
            return
        internal_types = ['invoice', 'debit_note', 'credit_note']
        domain = [('country_id.code', '=', 'CL'), ('internal_type', 'in', internal_types), ('active', '=', True)]
        documents = self.env['l10n_latam.document.type'].search(domain)
        for document in documents:
            sequence = self.env['ir.sequence'].create(document.get_document_sequence_vals(self))
            self.update({'l10n_cl_sequence_ids': [(4, {sequence.id})]})
        return

    @api.model
    def create(self, values):
        """ Create Document sequences after create the journal """
        res = super().create(values)
        res.create_document_sequences()
        return res
