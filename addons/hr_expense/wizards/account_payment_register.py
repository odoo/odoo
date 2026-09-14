from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def _get_line_batch_key(self, line):
        res = super()._get_line_batch_key(line)
        expense = line.move_id.expense_ids.filtered(
            lambda expense: expense.payment_mode == "own_account"
        )
        if expense and not line.move_id.partner_bank_id:
            _debug.logic("payment_bank_from_employee", expense=expense, line=line)
            res["partner_bank_id"] = (
                expense.employee_id.sudo().primary_bank_account_id.id
                or (line.partner_id.bank_ids and line.partner_id.bank_ids.ids[0])
            )
        return res

    def _init_payments(self, to_process, edit_mode=False):
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        for payment, vals in zip(payments, to_process, strict=True):
            expenses = vals["batch"]["lines"].expense_id
            if expenses:
                _debug.lifecycle(
                    "payment_linked_to_expense", payment=payment, expenses=expenses
                )
                payment.move_id.line_ids.write({"expense_id": expenses[0].id})
        return payments
