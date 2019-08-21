# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug.urls

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_split_str
from odoo.tools.misc import mod10r
from .res_bank import pretty_l10n_ch_postal


l10n_ch_ISR_NUMBER_LENGTH = 27
l10n_ch_ISR_NUMBER_ISSUER_LENGTH = 12

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ch_isr_subscription = fields.Char(compute='_compute_l10n_ch_isr_subscription', help='ISR subscription number identifying your company or your bank to generate ISR.')
    l10n_ch_isr_subscription_formatted = fields.Char(compute='_compute_l10n_ch_isr_subscription', help="ISR subscription number your company or your bank, formated with '-' and without the padding zeros, to generate ISR report.")

    l10n_ch_isr_number = fields.Char(compute='_compute_l10n_ch_isr_number', store=True, help='The reference number associated with this invoice')
    l10n_ch_isr_number_spaced = fields.Char(compute='_compute_l10n_ch_isr_number', help="ISR number split in blocks of 5 characters (right-justified), to generate ISR report.")

    l10n_ch_isr_optical_line = fields.Char(compute="_compute_l10n_ch_isr_optical_line", help='Optical reading line, as it will be printed on ISR')

    l10n_ch_isr_valid = fields.Boolean(compute='_compute_l10n_ch_isr_valid', help='Boolean value. True iff all the data required to generate the ISR are present')

    l10n_ch_isr_sent = fields.Boolean(default=False, help="Boolean value telling whether or not the ISR corresponding to this invoice has already been printed or sent by mail.")
    l10n_ch_currency_name = fields.Char(related='currency_id.name', readonly=True, string="Currency Name", help="The name of this invoice's currency") #This field is used in the "invisible" condition field of the 'Print ISR' button.

    @api.depends('invoice_partner_bank_id.l10n_ch_isr_subscription_eur', 'invoice_partner_bank_id.l10n_ch_isr_subscription_chf')
    def _compute_l10n_ch_isr_subscription(self):
        """ Computes the ISR subscription identifying your company or the bank that allows to generate ISR. And formats it accordingly"""

        def _format_isr_subscription_scanline(isr_subscription):
            # format the isr for scanline
            return isr_subscription[:2] + isr_subscription[2:-1].rjust(6, '0') + isr_subscription[-1:]

        for record in self:
            isr_subscription = False
            isr_subscription_formatted = False
            if record.invoice_partner_bank_id:
                if record.currency_id.name == 'EUR':
                    isr_subscription = record.invoice_partner_bank_id.l10n_ch_isr_subscription_eur
                elif record.currency_id.name == 'CHF':
                    isr_subscription = record.invoice_partner_bank_id.l10n_ch_isr_subscription_chf
                else:
                    #we don't format if in another currency as EUR or CHF
                    pass

                if isr_subscription:
                    isr_subscription = _format_isr_subscription_scanline(isr_subscription)
                    isr_subscription_formatted = pretty_l10n_ch_postal(isr_subscription)
            record.l10n_ch_isr_subscription = isr_subscription
            record.l10n_ch_isr_subscription_formatted = isr_subscription_formatted

    @api.depends('name', 'invoice_partner_bank_id.l10n_ch_isr_subscription_eur', 'invoice_partner_bank_id.l10n_ch_isr_subscription_chf')
    def _compute_l10n_ch_isr_number(self):
        """ The ISR reference number is 27 characters long. The first 12 of them
        contain the postal account number of this ISR's issuer, removing the zeros
        at the beginning and filling the empty places with zeros on the right if it is
        too short. The next 14 characters contain an internal reference identifying
        the invoice. For this, we use the invoice sequence number, removing each
        of its non-digit characters, and pad the unused spaces on the left of
        this number with zeros. The last character of the ISR number is the result
        of a recursive modulo 10 on its first 26 characters.
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
            isr_number = False
            isr_number_spaced = False
            if record.name and record.l10n_ch_isr_subscription:
                invoice_issuer_ref = re.sub('^0*', '', record.l10n_ch_isr_subscription)
                invoice_issuer_ref = invoice_issuer_ref.ljust(l10n_ch_ISR_NUMBER_ISSUER_LENGTH, '0')
                invoice_ref = re.sub('[^\d]', '', record.name)
                #We only keep the last digits of the sequence number if it is too long
                invoice_ref = invoice_ref[-l10n_ch_ISR_NUMBER_ISSUER_LENGTH:]
                internal_ref = invoice_ref.zfill(l10n_ch_ISR_NUMBER_LENGTH - l10n_ch_ISR_NUMBER_ISSUER_LENGTH - 1) # -1 for mod10r check character

                isr_number = mod10r(invoice_issuer_ref + internal_ref)
                isr_number_spaced = _space_isr_number(record.l10n_ch_isr_number)
            record.l10n_ch_isr_number = isr_number
            record.l10n_ch_isr_number_spaced = isr_number_spaced

    @api.depends(
        'currency_id.name', 'amount_total', 'name',
        'invoice_partner_bank_id.l10n_ch_postal',
        'invoice_partner_bank_id.l10n_ch_isr_subscription_eur',
        'invoice_partner_bank_id.l10n_ch_isr_subscription_chf')
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
            if record.l10n_ch_isr_number and record.l10n_ch_isr_subscription and record.currency_id.name:
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
                record.l10n_ch_isr_optical_line = left + '>' + record.l10n_ch_isr_number + '+ ' + record.l10n_ch_isr_subscription + '>'

    @api.depends(
        'type', 'name', 'currency_id.name',
        'invoice_partner_bank_id.l10n_ch_isr_subscription_eur',
        'invoice_partner_bank_id.l10n_ch_isr_subscription_chf')
    def _compute_l10n_ch_isr_valid(self):
        """Returns True if all the data required to generate the ISR are present"""
        for record in self:
            record.l10n_ch_isr_valid = record.type == 'out_invoice' and\
                record.name and \
                record.l10n_ch_isr_subscription and \
                record.l10n_ch_currency_name in ['EUR', 'CHF']

    def split_total_amount(self):
        """ Splits the total amount of this invoice in two parts, using the dot as
        a separator, and taking two precision digits (always displayed).
        These two parts are returned as the two elements of a tuple, as strings
        to print in the report.

        This function is needed on the model, as it must be called in the report
        template, which cannot reference static functions
        """
        return float_split_str(self.amount_total, 2)

    def display_swiss_qr_code(self):
        """ Trigger the print of the Swiss QR code in the invoice report or not
        """
        self.ensure_one()
        qr_parameter = self.env['ir.config_parameter'].sudo().get_param('l10n_ch.print_qrcode')
        return self.partner_id.country_id.code == 'CH' and qr_parameter

    def isr_print(self):
        """ Triggered by the 'Print ISR' button.
        """
        self.ensure_one()
        if self.l10n_ch_isr_valid:
            self.l10n_ch_isr_sent = True
            return self.env.ref('l10n_ch.l10n_ch_isr_report').report_action(self)
        else:
           raise ValidationError(_("""You cannot generate an ISR yet.\n
                                   For this, you need to :\n
                                   - set a valid postal account number (or an IBAN referencing one) for your company\n
                                   - define its bank\n
                                   - associate this bank with a postal reference for the currency used in this invoice\n
                                   - fill the 'bank account' field of the invoice with the postal to be used to receive the related payment. A default account will be automatically set for all invoices created after you defined a postal account for your company."""))

    def action_invoice_sent(self):
        # OVERRIDE
        rslt = super(AccountMove, self).action_invoice_sent()

        if self.l10n_ch_isr_valid:
            rslt['context']['l10n_ch_mark_isr_as_sent'] = True

        return rslt

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('l10n_ch_mark_isr_as_sent'):
            self.filtered(lambda inv: not inv.l10n_ch_isr_sent).write({'l10n_ch_isr_sent': True})
        return super(AccountMove, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    @api.model
    def _combine_address_fields(self, address):
        """Combine street fields in one string and zip + city in a second"""
        street_fields = ['street', 'street2']
        city_fields = ['zip', 'city']
        return [
            ' '.join(address[f] for f in street_fields if address[f]),
            ' '.join(address[f] for f in city_fields if address[f])
        ]

    @api.model
    def _build_swiss_code_url(
            self, iban, amount, currency, date_due, creditor,
            debitor, ref_type, reference, comment, bill_info):
        """
        https://www.paymentstandards.ch/dam/downloads/ig-qr-bill-en.pdf
        Chapter 4.3.3 Data elements in the QR-bill
        """
        communication = ""
        if comment:
            communication = (comment[:137] + '...') if len(comment) > 140 else comment
        cred_addr_lines = self._combine_address_fields(creditor)
        deb_addr_lines = self._combine_address_fields(debitor)
        cred_country_code = creditor.country_id.code
        deb_country_code = debitor.country_id.code

        qr_code_content = [
            # Header
            'SPC',                      # QRType
            '0200',                     # Version
            '1',                        # Coding type
            # Creditor information (Account / Payable to)
            iban,  # IBAN (IBAN or QR-IBAN)
            # + Creditor
            creditor.name,              # CR - Name
            'K',                        # CR - AdressTyp (S: structured, K: combined)
            cred_addr_lines[0],         # CR - Street or address line 1
            cred_addr_lines[1],         # CR - Building number or address line 2
            '',                         # CR - Postal code (keep empty with K)
            '',                         # CR - City (keep empty with K)
            cred_country_code,          # CR - Country
            # Ultimate creditor (In favor of) - Do not fill
            '',                         # UCR - Name
            '',                         # UCR - AdressTyp
            '',                         # UCR - Street or address line 1
            '',                         # UCR - Building number or address line 2
            '',                         # UCR - Postal code
            '',                         # UCR - City
            '',                         # UCR - Country
            # Payment amount information
            str(round(amount, 2)),      # Amount max 12-digits "." separator incl.
            currency,                   # Currency (CHF or EUR)
            # Ultimate Debtor (Payable by)
            debitor.name,               # UD - Name
            'K',                        # UD - AdressTyp (S: structured, K: combined)
            deb_addr_lines[0],          # UD - Street or address line 1
            deb_addr_lines[1],          # UD - Building number or address line 2
            '',                         # UD - Postal code (keep empty with K)
            '',                         # UD - City (keep empty with K)
            deb_country_code,           # UD - Country
            # Payment reference
            ref_type,                   # Reference type
            reference,                  # Reference
            # Additional information
            communication,              # Unstructured message
            'EPD',                      # Trailer
            bill_info,                  # Bill information (recommendation from Swico)
        ]

        qr_code_string = '\n'.join(qr_code_content)
        qr_code_url = '/report/barcode/?type=%s&value=%s&width=%s&height=%s&humanreadable=1' % ('QR', werkzeug.url_quote_plus(qr_code_string), 256, 256)
        return qr_code_url

    def build_swiss_code_url(self):
        return self._build_swiss_code_url(
            iban=self.invoice_partner_bank_id.sanitized_acc_number,
            amount=self.amount_residual,
            currency=self.currency_id.name,
            date_due=self.invoice_date_due,
            creditor=self.company_id,
            debitor=self.partner_id,
            ref_type='QRR',
            reference=self.l10n_ch_isr_number,
            comment=self.ref or self.name,
            bill_info='')

    def validate_swiss_code_arguments(self):
        """Account number must be a QR-IBAN to generate Swiss QR-Invoice
        """
        creditor = self.company_id
        debitor = self.partner_id
        bank_account = self.invoice_partner_bank_id

        return (bank_account.acc_type == 'qr-iban' and
                self.l10n_ch_isr_number and
                creditor.zip and
                creditor.city and
                (creditor.street or creditor.street2) and
                creditor.country_id.code and
                debitor.zip and
                debitor.city and
                (debitor.street or debitor.street2) and
                debitor.country_id.code)
