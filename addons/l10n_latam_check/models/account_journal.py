from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self.company_id.country_id.code == "AR" and self._is_payment_method_available('own_checks'):
            res |= self.env.ref('l10n_latam_check.account_payment_method_own_checks')
        return res

    @api.model
    def _get_reusable_payment_methods(self):
        """ We are able to have multiple times Checks payment method in a journal """
        res = super()._get_reusable_payment_methods()
        res.add("own_checks")
        return res
