# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class L10nLatamDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'

    l10n_cl_letter = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('I', 'I'),
        ('M', 'M'),
        ('R', 'R'),
        ('S', 'S'),
        ('T', 'T'),
        ('X', 'X'),
        ('L', 'L'),

    ],
        'Letters',
        help='We user letters structure to change the document behaviour inside odoo'
    )

    internal_type = fields.Selection(
        selection_add=[
            ('invoice', 'Invoices'),
            ('invoice_in', 'Purchase Invoices'),
            ('debit_note', 'Debit Notes'),
            ('credit_note', 'Credit Notes'),
            ('receipt_invoice', 'Receipt Invoice')])
    # take a look if I put here a fiscal position (preferred fiscal position).

    def get_document_sequence_vals(self, journal):
        values = super(L10nLatamDocumentType, self).get_document_sequence_vals(
            journal)
        if self.country_id != self.env.ref('base.cl'):
            return values
        values.update({
            'padding': 6,
            'implementation': 'no_gap',
            'l10n_latam_journal_id': journal.id
        })
        if journal.l10n_cl_share_sequences:
            values.update({'name': '%s - Letter %s Documents' % (journal.name, self.l10n_cl_letter),
                           'l10n_cl_letter': self.l10n_ck_letter})
        else:
            values.update({'name': '%s - %s' % (journal.name, self.name), 'l10n_latam_document_type_id': self.id})
        return values
