# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrExpenseRefuseWizard(models.TransientModel):
    """ Wizard to specify reason on expense sheet refusal """

    _name = "hr.expense.refuse.wizard"
    _description = "Expense Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    sheet_ids = fields.Many2many('hr.expense.sheet')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'sheet_ids' in fields:
            res['sheet_ids'] = self.env.context.get('active_ids', [])
        return res

    def action_refuse(self):
        self.sheet_ids._do_refuse(self.reason)
        return {'type': 'ir.actions.act_window_close'}
