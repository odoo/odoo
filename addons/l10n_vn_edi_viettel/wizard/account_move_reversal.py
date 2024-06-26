# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_vn_edi_adjustment_type = fields.Selection(
        string='Adjustment type',
        selection=[
            ('1', 'Money adjustment'),
            ('2', 'Information adjustment'),
        ],
    )
    l10n_vn_edi_agreement_document_name = fields.Char(
        string='Agreement Name',
    )
    l10n_vn_edi_agreement_document_date = fields.Datetime(
        string='Agreement Date',
    )

    def _prepare_default_reversal(self, move):
        # EXTEND 'account'
        values = super()._prepare_default_reversal(move)
        # This information is required when sending an adjustment invoice to sinvoice.
        # This is not needed when sending a replacement (as we will be sending the invoice, not the CN) but it doesn't hurt to log it.
        values.update({
            'l10n_vn_edi_agreement_document_name': self.l10n_vn_edi_agreement_document_name,
            'l10n_vn_edi_agreement_document_date': self.l10n_vn_edi_agreement_document_date,
            'l10n_vn_edi_adjustment_type': self.l10n_vn_edi_adjustment_type,
        })
        return values

    def _modify_move_default_values(self, origin_move):
        # EXTEND 'account'
        values = super()._modify_move_default_values(origin_move)
        # This information is REQUIRED on the new invoice that will be sent to sinvoice, if we are creating one.
        if origin_move.l10n_vn_edi_invoice_state not in {False, 'ready_to_send'}:
            values.update({
                'l10n_vn_edi_agreement_document_name': self.l10n_vn_edi_agreement_document_name,
                'l10n_vn_edi_agreement_document_date': self.l10n_vn_edi_agreement_document_date,
                'l10n_vn_edi_adjustment_type': self.l10n_vn_edi_adjustment_type,
                'l10n_vn_edi_replacement_origin': origin_move.id,
            })
        return values

    def reverse_moves(self, is_modify=False):
        # EXTEND 'account'
        for move in self.move_ids:
            # If an invoice has a tax code (symbol starts with C) and the code has not been approved by the tax authorities, you cannot adjust/reverse it.
            if move.l10n_vn_edi_invoice_state == 'sent' and move.l10n_vn_edi_invoice_symbol.name.startswith('C'):
                invoice_lookup, _error_message = move._l10n_vn_edi_lookup_invoice()
                if 'result' in invoice_lookup and invoice_lookup['result'][0].get('exchangeStatus') != 'INVOICE_HAS_CODE_APPROVED':
                    raise UserError(_('You cannot adjust/replace invoice %s, it has not been approved by the tax authorities.\n'
                                      'Please cancel/reverse it and create a new invoice instead.', move.name))

        action = super().reverse_moves(is_modify)

        # Makes sure to keep the original status up to date by tagging them by either replaced, or adjusted.
        if is_modify:
            self.move_ids.l10n_vn_edi_invoice_state = 'replaced'
        else:
            self.move_ids.l10n_vn_edi_invoice_state = 'adjusted'

        return action
