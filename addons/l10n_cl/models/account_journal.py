# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_cl_sequence_ids = fields.One2many(
        'ir.sequence', 'l10n_latam_journal_id', string="Sequences")
    l10n_cl_share_sequences = fields.Boolean(
        'Unified Book',
        help='Use same sequence for documents with the same letter')

    def get_journal_letter(self, counterpart_partner=False):
        """ Regarding the AFIP responsibility of the company and the type of journal (sale/purchase), get the allowed
        letters. Optionally, receive the counterpart partner (customer/supplier) and get the allowed letters to work
        with him. This method is used to populate document types on journals and also to filter document types on
        specific invoices to/from customer/supplier
        """
        self.ensure_one()
        # letters_data = {
        #     'issued': {
        #         '1': ['A', 'B', 'E', 'M'],
        #         '3': [],
        #         '4': ['C'],
        #         '5': [],
        #         '6': ['C', 'E'],
        #         '8': ['I'],
        #         '9': [],
        #         '10': [],
        #         '13': ['C', 'E'],
        #     },
        #     'received': {
        #         '1': ['A', 'C', 'M', 'I'],
        #         '3': ['B', 'C', 'I'],
        #         '4': ['B', 'C', 'I'],
        #         '5': ['B', 'C', 'I'],
        #         '6': ['B', 'C', 'I'],
        #         '8': ['E'],
        #         '9': ['E'],
        #         '10': ['E'],
        #         '13': ['B', 'C', 'I'],
        #     },
        # }
        #
        # letters = letters_data['issued' if self.type == 'sale' else 'received']
        # if not counterpart_partner:
        #     return letters
        #
        # counterpart_letters = letters_data['issued' if self.type == 'purchase' else 'received']
        # letters = list(set(letters) & set(counterpart_letters))
        # return letters

    def create_document_sequences(self):
        self.ensure_one()
        if self.company_id.country_id != self.env.ref('base.cl'):
            return True
        if not self.type == 'sale' or not self.l10n_latam_use_documents:
            return False

        sequences = self.l10n_cl_sequence_ids
        sequences.unlink()

        # Create Sequences
        # letters = self.get_journal_letter()
        internal_types = ['invoice', 'debit_note', 'credit_note']
        # domain = [('country_id.code', '=', 'CL'),
        #           ('internal_type', 'in', internal_types),
        #           '|', ('l10n_cl_letter', '=', False),
        #           ('l10n_cl_letter', 'in', letters)]
        domain = [
            ('country_id.code', '=', 'CL'),
            ('internal_type', 'in', internal_types),
            ('active', '=', True)
        ]
        # codes = self.get_journal_codes()
        # if codes:
        #     domain.append(('code', 'in', codes))
        documents = self.env['l10n_latam.document.type'].search(domain)
        for document in documents:
            if self.l10n_cl_share_sequences and self.l10n_cl_sequence_ids.filtered(
                    lambda x: x.l10n_cl_letter == document.l10n_cl_letter):
                continue

            sequences |= self.env['ir.sequence'].create(
                document.get_document_sequence_vals(self))
        return sequences

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



