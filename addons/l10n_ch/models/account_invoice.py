# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import mod10r

L10N_CH_QRR_NUMBER_LENGTH = 27


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ch_is_qr_valid = fields.Boolean(compute='_compute_l10n_ch_qr_is_valid', help="Determines whether an invoice can be printed as a QR or not")

    @api.depends('partner_id', 'currency_id')
    def _compute_l10n_ch_qr_is_valid(self):
        for move in self:
            error_messages = move.partner_bank_id._get_error_messages_for_qr('ch_qr', move.partner_id, move.currency_id)
            move.l10n_ch_is_qr_valid = (
                move.move_type == 'out_invoice' and
                not error_messages and
                (
                    # QR codes must be printed on all Swiss transactions
                    move.company_id.account_fiscal_country_id.code == 'CH' or
                    (
                        # QR code is also printed if the fiscal country is not Switzerland but the receivale account is eligible
                        move.partner_bank_id.acc_type == 'iban' and
                        (iban := (move.partner_bank_id.acc_number or '').replace(' ', '')).startswith('CH') and
                        iban[4:9].isdigit() and
                        30000 <= int(iban[4:9]) <= 31999
                    )
                )
            )

    def get_l10n_ch_qrr_number(self):
        """Generates the QRR reference.
        QRR references are 27 characters long.

        The invoice sequence number is used, removing each of its non-digit characters,
        and pad the unused spaces on the left of this number with zeros.
        The last digit is a checksum (mod10r).
        """
        self.ensure_one()
        if self.partner_bank_id.l10n_ch_qr_iban and self.l10n_ch_is_qr_valid and self.name:
            invoice_ref = re.sub(r'[^\d]', '', self.name)
            return self._compute_qrr_number(invoice_ref)
        else:
            return False

    @api.model
    def _compute_qrr_number(self, invoice_ref):
        # keep only the last digits if it exceed boundaries
        ref_payload_len = L10N_CH_QRR_NUMBER_LENGTH - 1
        extra = len(invoice_ref) - ref_payload_len
        if extra > 0:
            invoice_ref = invoice_ref[extra:]
        internal_ref = invoice_ref.zfill(ref_payload_len)
        return mod10r(internal_ref)

    def _get_invoice_reference_ch_invoice(self):
        """ This sets QRR reference number which is generated based on customer's `Bank Account` and set it as
        `Payment Reference` of the invoice when invoice's journal is using Switzerland's communication standard
        """
        self.ensure_one()
        return self.get_l10n_ch_qrr_number()

    def _get_invoice_reference_ch_partner(self):
        """ This sets QRR reference number which is generated based on customer's `Bank Account` and set it as
        `Payment Reference` of the invoice when invoice's journal is using Switzerland's communication standard
        """
        self.ensure_one()
        return self.get_l10n_ch_qrr_number()

    @api.model
    def space_qrr_reference(self, qrr_ref):
        """ Makes the provided QRR reference human-friendly, spacing its elements
        by blocks of 5 from right to left.
        """
        spaced_qrr_ref = ''
        i = len(qrr_ref) # i is the index after the last index to consider in substrings
        while i > 0:
            spaced_qrr_ref = qrr_ref[max(i-5, 0) : i] + ' ' + spaced_qrr_ref
            i -= 5
        return spaced_qrr_ref

    @api.model
    def space_scor_reference(self, iso11649_ref):
        """ Makes the provided SCOR reference human-friendly, spacing its elements
        by blocks of 5 from right to left.
        """
        return ' '.join(iso11649_ref[i:i + 4] for i in range(0, len(iso11649_ref), 4))

    def l10n_ch_action_print_qr(self):
        '''
        Checks that all invoices can be printed in the QR format.
        If so, launches the printing action.
        Else, triggers the l10n_ch wizard that will display the informations.
        '''
        if any(x.move_type != 'out_invoice' for x in self):
            raise UserError(_("Only customers invoices can be QR-printed."))
        if False in self.mapped('l10n_ch_is_qr_valid'):
            return {
                'name': (_("Some invoices could not be printed in the QR format")),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_ch.qr_invoice.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_ids': self.ids},
            }
        return self.env.ref('account.account_invoices').report_action(self)

    def _l10n_ch_dispatch_invoices_to_print(self):
        qr_invs = self.filtered('l10n_ch_is_qr_valid')
        return {
            'qr': qr_invs,
            'classic': self - qr_invs,
        }
