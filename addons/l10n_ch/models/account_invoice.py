# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, fields, api
from odoo.tools.float_utils import float_split_str
from odoo.tools.misc import mod10r


l10n_ch_ISR_NUMBER_LENGTH = 27
l10n_ch_ISR_NUMBER_ISSUER_LENGTH = 12

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    l10n_ch_isr_postal = fields.Char(compute='_compute_l10n_ch_isr_postal', help='The postal reference identifying the bank managing this ISR.')
    l10n_ch_isr_postal_formatted = fields.Char(compute='_compute_l10n_ch_isr_postal', help="Postal reference of the bank, formated with '-' and without the padding zeros, to generate ISR report.")

    l10n_ch_isr_number = fields.Char(compute='_compute_l10n_ch_isr_number', store=True, help='The reference number associated with this invoice')
    l10n_ch_isr_number_spaced = fields.Char(compute='_compute_l10n_ch_isr_number', help="ISR number split in blocks of 5 characters (right-justified), to generate ISR report.")

    l10n_ch_isr_optical_line = fields.Char(compute="_compute_l10n_ch_isr_optical_line", help='Optical reading line, as it will be printed on ISR')

    l10n_ch_isr_valid = fields.Boolean(compute='_compute_l10n_ch_isr_valid', help='Boolean value. True iff all the data required to generate the ISR are present')

    @api.depends('partner_bank_id.bank_id.l10n_ch_postal_eur', 'partner_bank_id.bank_id.l10n_ch_postal_chf')
    def _compute_l10n_ch_isr_postal(self):
        """ Computes the postal reference identifying the bank managing this ISR and formats it accordingly"""
        def _format_isr_postal(isr_postal):
            #format the isr as per specifications
            currency_code = isr_postal[:2]
            middle_part = isr_postal[2:-1]
            trailing_cipher = isr_postal[-1]
            middle_part = re.sub('^0*', '', middle_part)
            return currency_code + '-' + middle_part + '-' + trailing_cipher

        for record in self:
            if record.partner_bank_id and record.partner_bank_id.bank_id:
                isr_postal = False
                if record.currency_id.name == 'EUR':
                    isr_postal = record.partner_bank_id.bank_id.l10n_ch_postal_eur
                elif record.currency_id.name == 'CHF':
                    isr_postal = record.partner_bank_id.bank_id.l10n_ch_postal_chf
                else:
                    #we don't format if in another currency as EUR or CHF
                    continue

                if isr_postal:
                    record.l10n_ch_isr_postal = isr_postal
                    record.l10n_ch_isr_postal_formatted = _format_isr_postal(isr_postal)

    @api.depends('number', 'partner_bank_id.l10n_ch_postal')
    def _compute_l10n_ch_isr_number(self):
        """ The ISR reference number is 27 characters long. The first 12 of them
        contain the postal account number of this ISR's issuer, removing the zeros
        at the beginning and filling the empty places with zeros on the right if it is
        too short. The 15 other characters contain an internal reference identifying
        the invoice. For this, we use the invoice sequence number, removing each
        of its non-digit characters, and pad the unused spaces on the left of
        this number with zeros.
        """
        def _space_isr_number(isr_number):
            to_treat = isr_number
            res = ''
            while to_treat:
                res = to_treat[-5:] + res
                to_treat = to_treat[:-5]
                if to_treat:
                    res = ' ' + res
            return res

        for record in self:
            if record.number and record.partner_bank_id and record.partner_bank_id.l10n_ch_postal:
                invoice_issuer_ref = re.sub('^0*', '', record.partner_bank_id.l10n_ch_postal)
                invoice_issuer_ref = invoice_issuer_ref.ljust(l10n_ch_ISR_NUMBER_ISSUER_LENGTH, '0')
                invoice_ref = re.sub('[^\d]', '', record.number)
                #We only keep the last digits of the sequence number if it is too long
                invoice_ref = invoice_ref[-l10n_ch_ISR_NUMBER_ISSUER_LENGTH:]
                internal_ref = invoice_ref.zfill(l10n_ch_ISR_NUMBER_LENGTH - l10n_ch_ISR_NUMBER_ISSUER_LENGTH)

                record.l10n_ch_isr_number = invoice_issuer_ref + internal_ref
                record.l10n_ch_isr_number_spaced = _space_isr_number(record.l10n_ch_isr_number)

    @api.depends('currency_id.name', 'amount_total', 'partner_bank_id.bank_id', 'number', 'partner_bank_id.l10n_ch_postal', 'partner_bank_id.bank_id.l10n_ch_postal_eur', 'partner_bank_id.bank_id.l10n_ch_postal_chf')
    def _compute_l10n_ch_isr_optical_line(self):
        """ The optical reading line of the ISR looks like this :
                left>isr_ref+ bank_ref>

           Where:
           - left is composed of two ciphers indicating the currency (01 for CHF,
           03 for EUR), followed by ten characters containing the total of the
           invoice (with the dot between units and cents removed, everything being
           right-aligned and empty places filled with zeros). After the total,
           left contains a last cipher, which is the result of a recursive modulo
           10 function ran over the rest of it.

            - isr_ref is the ISR reference number

            - bank_ref is the full postal bank code (aka clearing number) of the
            bank supporting the ISR (including the zeros).
        """
        for record in self:
            if record.l10n_ch_isr_number and record.l10n_ch_isr_postal and record.currency_id.name:
                #Left part
                currency_code = None
                if record.currency_id.name == 'CHF':
                    currency_code = '01'
                elif record.currency_id.name == 'EUR':
                    currency_code = '03'
                units, cents = float_split_str(record.amount_total, 2)
                amount_to_display = units + cents
                amount_ref = amount_to_display.zfill(10)
                left = currency_code + amount_ref
                left = mod10r(left)
                #Final assembly (the space after the '+' is no typo, it stands in the specs.)
                record.l10n_ch_isr_optical_line = left + '>' + record.l10n_ch_isr_number + '+ ' + record.l10n_ch_isr_postal + '>'

    @api.depends('type', 'number', 'partner_bank_id.l10n_ch_postal', 'partner_bank_id.bank_id', 'currency_id.name', 'partner_bank_id.bank_id.l10n_ch_postal_eur', 'partner_bank_id.bank_id.l10n_ch_postal_chf')
    def _compute_l10n_ch_isr_valid(self):
        """Returns True if all the data required to generate the ISR are present"""
        for record in self:
            record.l10n_ch_isr_valid = record.type == 'out_invoice' and\
                record.number and \
                record.l10n_ch_isr_postal and \
                record.partner_bank_id and \
                record.partner_bank_id.l10n_ch_postal and \
                record.currency_id.name in ['EUR', 'CHF']

    def invoice_print(self):
        """ Triggered by the 'print invoice' button. When printing the invoice, also print
            the ISR if the invoice is compatible.
        """
        self.ensure_one()
        invoice_report = super(AccountInvoice, self).invoice_print()
        if self.l10n_ch_isr_valid:
            isr_report = self.env['report'].get_action(self, 'l10n_ch.isr_report_main')
            invoice_report['next_report_to_generate'] = isr_report
        return invoice_report
