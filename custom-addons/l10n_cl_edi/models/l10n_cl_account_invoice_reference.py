# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountInvoiceReference(models.Model):
    _name = 'l10n_cl.account.invoice.reference'
    _description = 'Cross Reference Docs for Chilean Electronic Invoicing'
    _rec_name = 'origin_doc_number'

    origin_doc_number = fields.Char(string='Origin Document Number',
                                    help='Origin document number, the document you are referring to', required=True)
    reference_doc_code = fields.Selection([
            ('1', '1. Cancels Referenced Document'),
            ('2', '2. Corrects Referenced Document Text'),
            ('3', '3. Corrects Referenced Document Amount')
    ], string='SII Reference Code',
        help='Use one of these codes for credit or debit notes that intend to change taxable data in the origin '
             'referred document')
    l10n_cl_reference_doc_type_id = fields.Many2one('l10n_latam.document.type', string='SII Doc Type Selector')
    l10n_cl_reference_doc_internal_type = fields.Selection(related='l10n_cl_reference_doc_type_id.internal_type',
                                                           string='Internal Type')
    reason = fields.Char(string='Reason')
    move_id = fields.Many2one('account.move', ondelete='cascade', string='Originating Document', index='btree_not_null')
    date = fields.Date(string='Document Date', required=True)
