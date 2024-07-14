# -*- coding: utf-8 -*-

from odoo import models, fields

from ..models.account_invoice import DESCRIPTION_DEBIT_CODE


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_co_edi_description_code_debit = fields.Selection(DESCRIPTION_DEBIT_CODE,
                                                          string="Concepto Nota de Débito", help="Colombian code for Debit Notes")

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
        default_values = super()._prepare_default_values(move)
        if move.company_id.country_id.code != "CO" or self.move_type not in ('in_refund', 'out_refund'):
            return default_values

        default_values['line_ids'] = [[5, 0, 0]]
        for line in move.line_ids.filtered(lambda x: x.display_type == 'product'):
            default_values['line_ids'].append([0, 0, {
                'product_id': line.product_id.id,
                'account_id': line.account_id.id,
                'analytic_distribution': line.analytic_distribution,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_repartition_line_id': self._get_repartition_line(line).id,
                'tax_ids': [[6, 0, line.tax_ids.ids]],
                'tax_tag_ids': self._get_opposite_tax_tag(line),
            }])
        return default_values

    def create_debit(self):
        action = super(AccountDebitNote, self).create_debit()
        if action.get('res_id'):
            debit_move = self.env['account.move'].browse(action['res_id'])
            debit_move.l10n_co_edi_description_code_debit = self.l10n_co_edi_description_code_debit
            debit_move.l10n_co_edi_operation_type = '30'
        return action
