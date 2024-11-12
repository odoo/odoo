# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
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
            raise UserError(_("OCR Reference Number length is greater than allowed. Allowed length in invoice journal setting is %s.", ocr_length))

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
        if self.partner_id and self.move_type == 'in_invoice' and self.partner_id.l10n_se_default_vendor_payment_ref:
            self.payment_reference = self.partner_id.l10n_se_default_vendor_payment_ref
        return super(AccountMove, self)._onchange_partner_id()

    @api.constrains('payment_reference', 'state')
    def _l10n_se_check_payment_reference(self):
        for invoice in self:
            if (
                (invoice.payment_reference or invoice.state == 'posted')
                and invoice.partner_id
                and invoice.move_type == 'in_invoice'
                and invoice.partner_id.l10n_se_check_vendor_ocr
                and invoice.country_code == 'SE'
            ):
                try:
                    luhn.validate(invoice.payment_reference)
                except Exception:
                    raise ValidationError(_("Vendor require OCR Number as payment reference. Payment reference isn't a valid OCR Number."))
