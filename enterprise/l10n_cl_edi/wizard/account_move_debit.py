# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountDebitNote(models.TransientModel):
    """
    Add Debit Note wizard: when you want to correct an invoice with a positive amount.
    Opposite of a Credit Note, but different from a regular invoice as you need the link to the original invoice.
    In some cases, also used to cancel Credit Notes
    """
    _name = 'account.debit.note'
    _inherit = 'account.debit.note'
    _description = 'Add Debit Note wizard'

    l10n_cl_edi_reference_doc_code = fields.Selection([
        ('1', '1. Cancels Referenced Document'),
        ('2', '2. Corrects Referenced Document Text'),
        ('3', '3. Corrects Referenced Document Amount')
    ], string='SII Reference Code')
    l10n_cl_original_text = fields.Char('Original Text', help='This is the text that is intended to be changed')
    l10n_cl_corrected_text = fields.Char('New Corrected Text', help='This is the text that should say')

    def _l10n_cl_get_reverse_doc_type(self, move):
        if move.partner_id.l10n_cl_sii_taxpayer_type == '4' or move.partner_id.country_id.code != "CL":
            return self.env['l10n_latam.document.type'].search([('code', '=', '111'), ('country_id.code', '=', "CL")], limit=1)
        return self.env['l10n_latam.document.type'].search([('code', '=', '56'), ('country_id.code', '=', "CL")], limit=1)

    def _get_opposite_tax_tag(self, line):
        # If we are making a debit note over a credit note, we need to use the reverse or opposite tax tag, for the
        # tax line and for the base line. get_tax_tags do the job, provided you pass the False value as the first
        # argument of the method.
        # the approach of getting the tax tags from the repartition line works only for the tax line and not for
        # the base line, since there is no repartition line for the base line.
        if line.tax_line_id:
            return [[6, 0, line.tax_line_id.get_tax_tags(False, 'tax').ids]]
        elif line.account_id.account_type not in ['asset_receivable', 'liability_payable']:
            return [[6, 0, line.tax_ids.get_tax_tags(False, 'base').ids]]
        return [[5]]

    def _get_repartition_line(self, line):
        if line.tax_repartition_line_id.document_type == 'refund':
            # for credit notes (refund) as originating document, we need to get the opposite repartition line
            return line.tax_repartition_line_id.tax_id.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == line.tax_repartition_line_id.repartition_type)
        # otherwise, the repartition line is the same as the originating doc (invoice for example)
        return line.tax_repartition_line_id

    def _prepare_default_values(self, move):
        # I would like to add the following line, because there is no case where you need to copy the lines
        # except for reverting a credit note, and this case is not included in the base code of credit note.
        # The only motivation to comment it is to prevent the test to fail.
        # self.copy_lines = True if self.l10n_cl_edi_reference_doc_code == '1' else False
        default_values = super(AccountDebitNote, self)._prepare_default_values(move)
        if move.company_id.account_fiscal_country_id.code != "CL" or not move.journal_id.l10n_latam_use_documents:
            return default_values
        reverse_move_latam_doc_type = self._l10n_cl_get_reverse_doc_type(move)
        default_values['invoice_origin'] = '%s %s' % (move.l10n_latam_document_type_id.doc_code_prefix,
                                                      move.l10n_latam_document_number)
        default_values['l10n_latam_document_type_id'] = reverse_move_latam_doc_type.id
        default_values['l10n_cl_reference_ids'] = [[0, 0, {
            'move_id': move.id,
            'origin_doc_number': move.l10n_latam_document_number,
            'l10n_cl_reference_doc_type_id': move.l10n_latam_document_type_id.id,
            'reference_doc_code': self.l10n_cl_edi_reference_doc_code,
            'reason': self.reason,
            'date': move.invoice_date, }, ], ]
        if self.l10n_cl_edi_reference_doc_code == '1':
            # this is needed to reverse a credit note: we must include the same items we have in the credit note
            # if we make this with traditional "with_context(internal_type='debit_note').copy(default=default_values)
            # the values will appear negative in the debit note
            default_values['line_ids'] = [[5, 0, 0]]
            for line in move.line_ids.filtered(lambda x: x.display_type in ('product', 'tax', 'payment_term')):
                default_values['line_ids'].append([0, 0, {
                    'product_id': line.product_id.id,
                    'account_id': line.account_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_repartition_line_id': self._get_repartition_line(line).id,
                    'tax_ids': [[6, 0, line.tax_ids.ids]],
                    'tax_tag_ids': self._get_opposite_tax_tag(line),
                    'discount': line.discount,
                    'display_type': line.display_type,
                }, ])
        elif self.l10n_cl_edi_reference_doc_code == '2':
            default_values['line_ids'] = [[5, 0, 0], [0, 0, {
                'account_id': move.journal_id.default_account_id.id,
                'name': _('Where it says: %(original_text)s should say: %(corrected_text)s',
                    original_text=self._context.get('default_l10n_cl_original_text'),
                    corrected_text=self._context.get('default_l10n_cl_corrected_text')),
                'quantity': 1,
                'price_unit': 0.0,
            }]]
        return default_values

    def create_debit(self):
        for move in self.move_ids.filtered(
            lambda r: r.company_id.account_fiscal_country_id.code == "CL" and
            r.move_type in ['out_invoice', 'out_refund'] and
            r.l10n_cl_journal_point_of_sale_type == 'online' and
            r.l10n_cl_dte_status not in ['accepted', 'objected']
        ):
            raise UserError(_('You can add a debit note only if the %s is accepted or objected by SII. ', move.name))
        return super(AccountDebitNote, self).create_debit()
