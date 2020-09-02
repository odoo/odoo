# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_split_str
from odoo.tools.misc import mod10r


l10n_ch_ISR_NUMBER_LENGTH = 27
l10n_ch_ISR_NUMBER_ISSUER_LENGTH = 12

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ch_isr_subscription = fields.Char(compute='_compute_l10n_ch_isr_subscription', help='ISR subscription number identifying your company or your bank to generate ISR.')
    l10n_ch_isr_subscription_formatted = fields.Char(compute='_compute_l10n_ch_isr_subscription', help="ISR subscription number your company or your bank, formated with '-' and without the padding zeros, to generate ISR report.")

    l10n_ch_isr_number = fields.Char(compute='_compute_l10n_ch_isr_number', store=True, help='The reference number associated with this invoice')
    l10n_ch_isr_number_spaced = fields.Char(compute='_compute_l10n_ch_isr_number_spaced', help="ISR number split in blocks of 5 characters (right-justified), to generate ISR report.")

    l10n_ch_isr_optical_line = fields.Char(compute="_compute_l10n_ch_isr_optical_line", help='Optical reading line, as it will be printed on ISR')

    l10n_ch_isr_valid = fields.Boolean(compute='_compute_l10n_ch_isr_valid', help='Boolean value. True iff all the data required to generate the ISR are present')

    l10n_ch_isr_sent = fields.Boolean(default=False, help="Boolean value telling whether or not the ISR corresponding to this invoice has already been printed or sent by mail.")
    l10n_ch_currency_name = fields.Char(related='currency_id.name', readonly=True, string="Currency Name", help="The name of this invoice's currency") #This field is used in the "invisible" condition field of the 'Print ISR' button.
    l10n_ch_isr_needs_fixing = fields.Boolean(compute="_compute_l10n_ch_isr_needs_fixing", help="Used to show a warning banner when the vendor bill needs a correct ISR payment reference. ")

    @api.depends('invoice_partner_bank_id.l10n_ch_isr_subscription_eur', 'invoice_partner_bank_id.l10n_ch_isr_subscription_chf')
    def _compute_l10n_ch_isr_subscription(self):
        """ Computes the ISR subscription identifying your company or the bank that allows to generate ISR. And formats it accordingly"""
        def _format_isr_subscription(isr_subscription):
            #format the isr as per specifications
            currency_code = isr_subscription[:2]
            middle_part = isr_subscription[2:-1]
            trailing_cipher = isr_subscription[-1]
            middle_part = re.sub('^0*', '', middle_part)
            return currency_code + '-' + middle_part + '-' + trailing_cipher

        def _format_isr_subscription_scanline(isr_subscription):
            # format the isr for scanline
            return isr_subscription[:2] + isr_subscription[2:-1].rjust(6, '0') + isr_subscription[-1:]

        for record in self:
            record.l10n_ch_isr_subscription = False
            record.l10n_ch_isr_subscription_formatted = False
            if record.invoice_partner_bank_id:
                if record.currency_id.name == 'EUR':
                    isr_subscription = record.invoice_partner_bank_id.l10n_ch_isr_subscription_eur
                elif record.currency_id.name == 'CHF':
                    isr_subscription = record.invoice_partner_bank_id.l10n_ch_isr_subscription_chf
                else:
                    #we don't format if in another currency as EUR or CHF
                    continue

                if isr_subscription:
                    isr_subscription = isr_subscription.replace("-", "")  # In case the user put the -
                    record.l10n_ch_isr_subscription = _format_isr_subscription_scanline(isr_subscription)
                    record.l10n_ch_isr_subscription_formatted = _format_isr_subscription(isr_subscription)

    @api.depends('name', 'invoice_partner_bank_id.l10n_ch_postal', 'invoice_partner_bank_id.acc_number')
    def _compute_l10n_ch_isr_number(self):
        """ The QRR or ISR reference number is 27 characters long. The first 12 of them
        contain the postal account number of this ISR's issuer, removing the zeros
        at the beginning and filling the empty places with zeros on the right if it is
        too short. The next 14 characters contain an internal reference identifying
        the invoice. For this, we use the invoice sequence number, removing each
        of its non-digit characters, and pad the unused spaces on the left of
        this number with zeros. The last character of the ISR number is the result
        of a recursive modulo 10 on its first 26 characters.
        """
        for record in self:
            has_qriban = record.invoice_partner_bank_id and record.invoice_partner_bank_id._is_qr_iban() or False
            isr_subscription = (record.invoice_partner_bank_id.l10n_ch_postal or '').replace("-", "")  # In case the user put the -
            if (has_qriban or isr_subscription) and record.name:
                invoice_issuer_ref = (isr_subscription or '').ljust(l10n_ch_ISR_NUMBER_ISSUER_LENGTH, '0')
                invoice_ref = re.sub('[^\d]', '', record.name)
                #We only keep the last digits of the sequence number if it is too long
                invoice_ref = invoice_ref[-l10n_ch_ISR_NUMBER_ISSUER_LENGTH:]
                internal_ref = invoice_ref.zfill(l10n_ch_ISR_NUMBER_LENGTH - l10n_ch_ISR_NUMBER_ISSUER_LENGTH - 1) # -1 for mod10r check character
                record.l10n_ch_isr_number = mod10r(invoice_issuer_ref + internal_ref)
            else:
                record.l10n_ch_isr_number = False

    @api.depends('l10n_ch_isr_number')
    def _compute_l10n_ch_isr_number_spaced(self):
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
            if record.name and record.invoice_partner_bank_id and record.invoice_partner_bank_id.l10n_ch_postal:
                record.l10n_ch_isr_number_spaced = _space_isr_number(record.l10n_ch_isr_number)
            else:
                record.l10n_ch_isr_number_spaced = False


    @api.depends(
        'currency_id.name', 'amount_residual', 'name',
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
            record.l10n_ch_isr_optical_line = ''
            if record.l10n_ch_isr_number and record.l10n_ch_isr_subscription and record.currency_id.name:
                #Left part
                currency_code = None
                if record.currency_id.name == 'CHF':
                    currency_code = '01'
                elif record.currency_id.name == 'EUR':
                    currency_code = '03'
                units, cents = float_split_str(record.amount_residual, 2)
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

    @api.depends('type', 'invoice_partner_bank_id', 'invoice_payment_ref')
    def _compute_l10n_ch_isr_needs_fixing(self):
        for inv in self:
            if inv.type == 'in_invoice' and inv.company_id.country_id.code == "CH":
                partner_bank = inv.invoice_partner_bank_id
                if partner_bank._is_isr_issuer() and not inv._has_isr_ref():
                    inv.l10n_ch_isr_needs_fixing = True
                    continue
            inv.l10n_ch_isr_needs_fixing = False

    def _has_isr_ref(self):
        """Check if this invoice has a valid ISR reference (for Switzerland)
        e.g.
        12371
        000000000000000000000012371
        210000000003139471430009017
        21 00000 00003 13947 14300 09017
        """
        self.ensure_one()
        ref = self.invoice_payment_ref or self.ref
        if not ref:
            return False
        ref = ref.replace(' ', '')
        if re.match(r'^(\d{2,27})$', ref):
            return ref == mod10r(ref[:-1])
        return False

    def split_total_amount(self):
        """ Splits the total amount of this invoice in two parts, using the dot as
        a separator, and taking two precision digits (always displayed).
        These two parts are returned as the two elements of a tuple, as strings
        to print in the report.

        This function is needed on the model, as it must be called in the report
        template, which cannot reference static functions
        """
        return float_split_str(self.amount_residual, 2)

    def display_swiss_qr_code(self):
        """ DEPRECATED FUNCTION: not used anymore. QR-bills can now always
        be generated, with a dedicated report
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

    def can_generate_qr_bill(self):
        """ Returns True iff the invoice can be used to generate a QR-bill.
        """
        self.ensure_one()

        # First part of this condition is due to fix commit https://github.com/odoo/odoo/commit/719f087b1b5be5f1f276a0f87670830d073f6ef4
        # We do that to ensure not to try generating QR-bills for modules that haven't been
        # updated yet. Not doing that could crash when trying to send an invoice by mail,
        # as the QR report data haven't been loaded.
        # TODO: remove this in master
        return not self.env.ref('l10n_ch.l10n_ch_swissqr_template').inherit_id \
               and self.invoice_partner_bank_id.validate_swiss_code_arguments(self.invoice_partner_bank_id.currency_id, self.partner_id, self.invoice_payment_ref)

    def print_ch_qr_bill(self):
        """ Triggered by the 'Print QR-bill' button.
        """
        self.ensure_one()

        if not self.can_generate_qr_bill():
            raise UserError(_("Cannot generate the QR-bill. Please check you have configured the address of your company and debtor. If you are using a QR-IBAN, also check the invoice's payment reference is a QR reference."))

        self.l10n_ch_isr_sent = True
        return self.env.ref('l10n_ch.l10n_ch_qr_report').report_action(self)

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

    def _get_invoice_reference_ch_invoice(self):
        """ This sets ISR reference number which is generated based on customer's `Bank Account` and set it as
        `Payment Reference` of the invoice when invoice's journal is using Switzerland's communication standard
        """
        self.ensure_one()
        return self.l10n_ch_isr_number

    def _get_invoice_reference_ch_partner(self):
        """ This sets ISR reference number which is generated based on customer's `Bank Account` and set it as
        `Payment Reference` of the invoice when invoice's journal is using Switzerland's communication standard
        """
        self.ensure_one()
        return self.l10n_ch_isr_number

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
