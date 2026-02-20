# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('wire_transfer'):
            res |= self.env.ref('payment_custom.account_payment_method_wire_transfer')
        return res
