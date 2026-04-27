from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # _sudo as it just computes if a warning should be present and has to pass through several models whose rights are very differents
    is_already_paid_through_a_payslip = fields.Boolean(compute='_compute_is_already_paid_through_a_payslip', compute_sudo=True)

    @api.depends('line_ids.move_id')
    def _compute_is_already_paid_through_a_payslip(self):
        """
        Computes the display of a warning in the form view that would prevent paying an expense move
        already set to be paid through a payslip
        """
        for wizard in self:
            wizard.is_already_paid_through_a_payslip = bool(wizard.line_ids.move_id.expense_sheet_id.payslip_id)
