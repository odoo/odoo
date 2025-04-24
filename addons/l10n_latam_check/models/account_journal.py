from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _get_reusable_payment_methods(self):
        """ We are able to have multiple times Checks payment method in a journal """
        res = super()._get_reusable_payment_methods()
        res.add("own_checks")
        return res
