#  Copyright (c) by The Bean Family, 2023.
#
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
#  These code are maintained by The Bean Family.

from odoo import models, api, _


# Customize the res_partner_bank model
#     - Override the original 'retrieve_acc_type' function to add more bank account type.

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    # This section is Override the original 'retrieve_acc_type' function:
    #     Logic:
    #         - Check if "acc_number" is start with '9704', that is the 'Vietnam Debit/Credit Card Account'
    #         - Otherwise, that is a bank account
    @api.model
    def retrieve_acc_type(self, acc_number):
        if str(acc_number).startswith("9704"):
            return 'vdcc'
        else:
            return super().retrieve_acc_type(acc_number)

    # This section is Override the original '_get_supported_account_types' function_
    #    -  The original Odoo only support 'bank' or 'IBAN' type
    #    -  Add 'vdcc' type, which stand for 'Vietnam Debit/Credit Card Account'
    @api.model
    def _get_supported_account_types(self):
        result: list = super()._get_supported_account_types()
        result.append(('vdcc', _('Vietnam Debit/Credit Card Account')))
        return result
