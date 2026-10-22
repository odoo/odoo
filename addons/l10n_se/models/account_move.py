# Part of Odoo. See LICENSE file for full copyright and licensing details.

from stdnum import luhn

from odoo import api, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    """Extend account.move with Swedish OCR reference generation and validation."""
    _inherit = 'account.move'

    def _get_invoice_reference_se_ocr2(self, reference):
        self.ensure_one()
        return reference + luhn.calc_check_digit(reference)

    def _get_invoice_reference_se_ocr3(self, reference):
        self.ensure_one()
        # Length digit: total length incl. length and check digit; units digit when 10 or more (Bankgirot)
        reference = reference + str((len(reference) + 2) % 10)
        return reference + luhn.calc_check_digit(reference)

    def _get_invoice_reference_se_ocr4(self, reference):
        self.ensure_one()

        ocr_length = self.journal_id.l10n_se_invoice_ocr_length

        if len(reference) + 1 > ocr_length:
            raise UserError(self.env._("OCR Reference Number length is greater than allowed. Allowed length in invoice journal setting is %s.", ocr_length))

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
        customer = self.partner_id.commercial_partner_id
        return self._get_invoice_reference_se_ocr2(customer.ref if str(customer.ref).isdecimal() else str(customer.id))

    def _get_invoice_reference_se_ocr3_partner(self):
        self.ensure_one()
        customer = self.partner_id.commercial_partner_id
        return self._get_invoice_reference_se_ocr3(customer.ref if str(customer.ref).isdecimal() else str(customer.id))

    def _get_invoice_reference_se_ocr4_partner(self):
        self.ensure_one()
        customer = self.partner_id.commercial_partner_id
        return self._get_invoice_reference_se_ocr4(customer.ref if str(customer.ref).isdecimal() else str(customer.id))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ If Vendor Bill and Vendor OCR is set, add it. """
        vendor = self.partner_id.commercial_partner_id
        if vendor and self.move_type == 'in_invoice' and vendor.l10n_se_default_vendor_payment_ref:
            self.payment_reference = vendor.l10n_se_default_vendor_payment_ref
        return super()._onchange_partner_id()

    def _l10n_se_requires_ocr_validation(self):
        """Return True if this invoice requires OCR reference validation.

        A reference is validated as soon as it is entered; a posted bill
        from a vendor that requires OCR must have one.

        :return: True if the invoice is an SE vendor bill with OCR check enabled
            that has a payment reference or is posted.
        :rtype: bool
        """
        return (
            (self.payment_reference or self.state == 'posted')
            and self.move_type == 'in_invoice'
            and self.country_code == 'SE'
            and self.commercial_partner_id.l10n_se_check_vendor_ocr
        )

    def _l10n_se_validate_ocr_reference(self):
        """Validate the OCR payment reference using the Luhn algorithm.

        :raises ValidationError: if the payment reference is not a valid OCR number.
        """
        try:
            luhn.validate(self.payment_reference)
        except Exception as exc:
            raise ValidationError(self.env._(
                "Vendor require OCR Number as payment reference. "
                "Payment reference isn't a valid OCR Number.",
            )) from exc

    @api.constrains('payment_reference', 'state')
    def _l10n_se_check_payment_reference(self):
        """Validate OCR payment reference on posted vendor bills when required."""
        for invoice in self:
            if invoice._l10n_se_requires_ocr_validation():
                invoice._l10n_se_validate_ocr_reference()
