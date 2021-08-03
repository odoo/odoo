from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _default_outbound_payment_methods(self):
        if self._context.get('third_checks_journal'):
            return self.env.ref('l10n_ar_third_check.account_payment_method_out_third_checks')
        return super()._default_outbound_payment_methods()

    def _default_inbound_payment_methods(self):
        if self._context.get('third_checks_journal'):
            return self.env.ref('l10n_ar_third_check.account_payment_method_new_third_checks') + self.env.ref('l10n_ar_third_check.account_payment_method_in_third_checks')

        return super()._default_inbound_payment_methods()
