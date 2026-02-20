import re
from stdnum import luhn

from odoo import models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_reference_dk_fik_invoice(self):
        self.ensure_one()
        creditor_number = self.journal_id.l10n_dk_fik_creditor_number
        invoice_digits = re.sub(r"\D", "", self.name or "") or str(self.id)
        if len(invoice_digits) > 15:
            raise ValidationError(
                "Invoice number contains more than 15 digits; cannot generate a valid FIK reference."
            )

        if len(invoice_digits) == 15:
            type_prefix = "75"
            payment_id = invoice_digits
        else:
            type_prefix = "71"
            payment_id = invoice_digits.zfill(14)

        check_digit = luhn.calc_check_digit(payment_id)
        return f"+{type_prefix}<{payment_id}{check_digit}+{creditor_number}<"
