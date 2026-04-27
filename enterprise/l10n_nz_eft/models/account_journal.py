# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # ---------------
    # Default methods
    # ---------------

    def _default_inbound_payment_methods(self):
        # EXTENDS account
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('l10n_nz_eft_in'):
            res |= self.env.ref('l10n_nz_eft.account_payment_method_eft_inbound')
        return res

    def _default_outbound_payment_methods(self):
        # EXTENDS account
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available('l10n_nz_eft_out'):
            res |= self.env.ref('l10n_nz_eft.account_payment_method_eft_outbound')
        return res
