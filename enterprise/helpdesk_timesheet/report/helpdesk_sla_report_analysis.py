# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskSLAReport(models.Model):
    _inherit = 'helpdesk.sla.report.analysis'

    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    total_hours_spent = fields.Float(
        "Hours Spent (Timesheets)",
        aggregator="avg",
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )

    def _select(self):
        return super()._select() + """,
            DEP.id as department_id,
            EMP.parent_id as manager_id,
            EMP.id as employee_id,
            NULLIF(T.total_hours_spent, 0) AS total_hours_spent
        """

    def _group_by(self):
        return super()._group_by() + """ ,
            DEP.id,
            EMP.parent_id,
            EMP.id,
            T.total_hours_spent
        """

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN "res_users" U on T.user_id = U.id AND U.company_id = T.company_id
            LEFT JOIN "hr_employee" EMP on EMP.user_id = U.id AND EMP.company_id = T.company_id
            LEFT JOIN "hr_department" DEP on EMP.department_id = DEP.id AND DEP.company_id = T.company_id
        """
        return from_str
