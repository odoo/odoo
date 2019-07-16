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

    @api.multi
    def get_document_sequence_vals(self, journal):
        vals = super(L10nLatamDocumentType, self).get_document_sequence_vals(
            journal)
        if self.country_id.code == 'CL':
            vals.update({
                'padding': 6,
                'implementation': 'no_gap',
            })
        return vals
