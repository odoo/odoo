# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrExpenseApproveDuplicate(models.TransientModel):
    """
    This wizard is shown whenever an approved expense is similar to one being
    approved. The user has the opportunity to still validate it or decline.
    """

    _name = 'hr.expense.approve.duplicate'
    _description = "Expense Approve Duplicate"

    sheet_ids = fields.Many2many('hr.expense.sheet')
    expense_ids = fields.Many2many('hr.expense', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        if 'sheet_ids' in fields:
            res['sheet_ids'] = [(6, 0, self.env.context.get('default_sheet_ids', []))]
        if 'duplicate_expense_ids' in fields:
            res['expense_ids'] = [(6, 0, self.env.context.get('default_expense_ids', []))]

        return res

    def action_approve(self):
        self.sheet_ids._do_approve()
        return {'type': 'ir.actions.act_window_close'}

    def action_refuse(self):
        self.sheet_ids._do_refuse(_('Duplicate Expense'))
        return {'type': 'ir.actions.act_window_close'}
