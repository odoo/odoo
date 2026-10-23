from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        # EXTENDS sale
        # A confirmed online payment posts the invoices it pays and reconciles them at once: the
        # customer gets them right away, so they are issued as they are posted.
        return super(PaymentTransaction, self.with_context(l10n_pt_issue_automatically=True))._post_process()
