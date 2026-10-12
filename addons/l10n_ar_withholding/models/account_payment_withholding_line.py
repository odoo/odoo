from odoo import models


class AccountPaymentWithholdingLine(models.Model):
    _inherit = 'account.payment.withholding.line'

    def _l10n_ar_get_payment(self):
        return self.payment_id
