# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    # _refund_cleanup_lines nu se mai gaseste in 13.
    # @api.model
    # def _refund_cleanup_lines(self, lines):
    #     result = super(AccountInvoice, self.with_context(mode='modify'))._refund_cleanup_lines(lines)
    #     return result
