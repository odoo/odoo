from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('riba'):
            res |= self.env.ref('l10n_it_riba.payment_method_riba')
        return res
