# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    od19_approval_hint = fields.Char(
        string='Waiting On / รออนุมัติจาก',
        compute='_compute_od19_approval_hint',
    )

    @api.depends('state')
    def _compute_od19_approval_hint(self):
        # Phase 1 (tier validation) adds ``review_ids`` to hr.expense. Until
        # that lands in this branch, fall back to a plain label derived from
        # ``state`` (plan constraint C1).
        has_tier = 'review_ids' in self.env['hr.expense']._fields
        for expense in self:
            if expense.state == 'submitted' and has_tier:
                pending = expense.review_ids.filtered(
                    lambda r: r.status == 'pending')
                expense.od19_approval_hint = (
                    pending[:1].name or _('Waiting approval'))
            else:
                expense.od19_approval_hint = dict(
                    expense._fields['state'].selection).get(expense.state, '')
