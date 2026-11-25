# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_taxable_supply_date_used(self):
        # EXTENDS 'account'
        return self.country_code == 'SK' or super()._is_taxable_supply_date_used()

    def _generate_qr_code(self, silent_errors=False):
        """ Forward the due date to the QR-code generation.

        The PAY by square data model carries the payment due date, which the
        generic QR-code generation signature does not provide.
        """
        # EXTENDS account
        self.ensure_one()
        return super(
            AccountMove,
            self.with_context(invoice_date_due=self.invoice_date_due),
        )._generate_qr_code(silent_errors)
