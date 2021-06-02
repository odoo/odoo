# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from stdnum import luhn


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoice_reference_se_ocr2(self, reference):
        self.ensure_one()
        return reference + luhn.calc_check_digit(reference)

    def _get_invoice_reference_se_ocr3(self, reference):
        self.ensure_one()
        reference = reference + str(len(reference) + 2)[:1]
        return reference + luhn.calc_check_digit(reference)

    def _get_invoice_reference_se_ocr4(self, reference):
        self.ensure_one()

        ocr_length = self.journal_id.l10n_se_invoice_ocr_length

        if len(reference) + 1 > ocr_length:
            raise UserError(_("OCR Reference Number length is greater than allowed. Allowed length in invoice journal setting is %s.") % str(ocr_length))

        reference = reference.rjust(ocr_length - 1, '0')
        return reference + luhn.calc_check_digit(reference)


    def _get_invoice_reference_se_ocr2_invoice(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr2(str(self.id))

    def _get_invoice_reference_se_ocr3_invoice(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr3(str(self.id))

    def _get_invoice_reference_se_ocr4_invoice(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr4(str(self.id))

    def _get_invoice_reference_se_ocr2_partner(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr2(self.partner_id.ref if str(self.partner_id.ref).isdecimal() else str(self.partner_id.id))

    def _get_invoice_reference_se_ocr3_partner(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr3(self.partner_id.ref if str(self.partner_id.ref).isdecimal() else str(self.partner_id.id))

    def _get_invoice_reference_se_ocr4_partner(self):
        self.ensure_one()
        return self._get_invoice_reference_se_ocr4(self.partner_id.ref if str(self.partner_id.ref).isdecimal() else str(self.partner_id.id))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ If Vendor Bill and Vendor OCR is set, add it. """
        if self.partner_id and self.type == 'in_invoice' and self.partner_id.l10n_se_default_vendor_payment_ref:
            self.invoice_payment_ref = self.partner_id.l10n_se_default_vendor_payment_ref
        return super(AccountMove, self)._onchange_partner_id()

    @api.onchange('invoice_payment_ref')
    def _onchange_invoice_payment_ref(self):
        """ If Vendor Bill and Payment Reference is changed check validation. """
        if self.partner_id and self.type == 'in_invoice' and self.partner_id.l10n_se_check_vendor_ocr:
            reference = self.invoice_payment_ref
            try:
                luhn.validate(reference)
            except: 
                return {'warning': {'title': _('Warning'), 'message': _('Vendor require OCR Number as payment reference. Payment reference isn\'t a valid OCR Number.')}}
        return super(AccountMove, self)._onchange_invoice_payment_ref()
