# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models, _


class HrExpenseApproveDuplicate(models.TransientModel):
    """
    This wizard is shown whenever an approved expense is similar to one being
    approved. The user has the opportunity to still validate it or decline.
    """

    _name = 'hr.expense.approve.duplicate'
    _description = "Expense Approve Duplicate"

    expense_ids = fields.Many2many('hr.expense', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'duplicate_expense_ids' in fields:
            res['expense_ids'] = [Command.set(self.env.context.get('default_expense_ids', []))]
        return res

    def action_approve(self):
        self.expense_ids.filtered(lambda expense: expense.state == 'submitted')._do_approve()
        return {'type': 'ir.actions.act_window_close'}

    def action_refuse(self):
        self.expense_ids.filtered(lambda expense: expense.state == 'submitted')._do_refuse(_('Duplicate Expense'))
        return {'type': 'ir.actions.act_window_close'}
