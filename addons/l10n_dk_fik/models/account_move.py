import re
from stdnum import luhn

from odoo import models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_reference_dk_fik(self, prefix, max_digits):
        self.ensure_one()
        invoice_digits = re.sub(r"\D", "", self.name or "") or str(self.id)
        if len(invoice_digits) > max_digits:
            raise ValidationError(
                self.env._(
                    "FIK %(prefix)s reference cannot be generated: invoice number '%(invoice)s' has more than %(max_digits)s digits."
                ) % {
                    "prefix": prefix,
                    "invoice": self.name,
                    "max_digits": max_digits,
                }
            )
        payment_id = invoice_digits.zfill(max_digits)
        check_digit = luhn.calc_check_digit(payment_id)
        creditor_number = self.journal_id.l10n_dk_fik_creditor_number

        return f"+{prefix}<{payment_id}{check_digit}+{creditor_number}<"

    def _get_invoice_reference_dk_fik_71_invoice(self):
        return self._get_invoice_reference_dk_fik("71", 14)

    def _get_invoice_reference_dk_fik_75_invoice(self):
        return self._get_invoice_reference_dk_fik("75", 15)
