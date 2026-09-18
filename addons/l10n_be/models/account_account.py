from odoo import models

deferred_codes = frozenset({
    '168000', '168100', '168200', '168700', '168800',
    '451057', '490000', '493000', '680000', '780000',
})


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def is_deferred_account(self):
        return self.code in deferred_codes or super().is_deferred_account()
