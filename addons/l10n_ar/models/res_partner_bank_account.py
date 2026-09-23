import logging

from stdnum.ar.cbu import validate

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class ResPartnerBankAccount(models.Model):
    _inherit = "res.partner.bank.account"

    @api.model
    def _get_account_types_supported(self):
        """Add new account type named cbu used in Argentina"""
        res = super()._get_account_types_supported()
        res.append(("cbu", _("CBU")))
        return res

    @api.model
    def _get_acc_type(self, acc_number):
        try:
            validate(acc_number)
        except ValueError:
            return super()._get_acc_type(acc_number)
        return "cbu"
