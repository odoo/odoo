# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import fields, models
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    slot_id = fields.Many2one('planning.slot', 'Planning Shift', index='btree_not_null')

    def _group_expand_employee_ids(self, employees, domain, order):
        res = super()._group_expand_employee_ids(employees, domain, order)
        employee = self.env.user.employee_id
        if not employee or any(isinstance(term, (list, tuple)) and term[0] == 'employee_id' for term in domain):
            return res

        slot_count = self.env['planning.slot'].search_count(
            self._get_planning_domain(employee.id), limit=1
        )
        if slot_count:
            res |= employee
        return res

    def _get_planning_domain(self, employee_id):
        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = fields.Datetime.from_string(self.env.context.get('grid_anchor', today))
        grid_range = self.env.context.get('grid_range', 'week')

        period_start = grid_anchor if grid_range == 'days'\
            else grid_anchor - relativedelta(days=grid_anchor.weekday() + 1) if grid_range == 'week'\
            else grid_anchor + relativedelta(day=1)
        period_end = period_start + relativedelta(**{grid_range + 's': 1})

        planning_domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'published'),
            ('project_id.allow_timesheets', '=', True),
            ('start_datetime', '<', period_end),
            ('end_datetime', '>', period_start),
        ]
        return planning_domain
