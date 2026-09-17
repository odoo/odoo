from odoo import models

deferred_codes = frozenset({
    '487000',
})


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def is_deferred_account(self):
        return self.code in deferred_codes or super().is_deferred_account()
