# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicketReport(models.Model):
    _inherit = 'helpdesk.ticket.report.analysis'

    total_hours_spent = fields.Float("Hours Spent", group_operator="avg", readonly=True)
    employee_parent_id = fields.Many2one('hr.employee', string='Manager', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += """,
            NULLIF(T.total_hours_spent, 0) AS total_hours_spent,
            EMP.parent_id AS employee_parent_id,
            DEP.id AS department_id,
            EMP.id AS employee_id,
            T.analytic_account_id as analytic_account_id
        """
        return select_str

    def _group_by(self):
        return super()._group_by() + """ ,
            DEP.id,
            EMP.parent_id,
            EMP.id,
            T.total_hours_spent,
            T.analytic_account_id
        """

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN res_users U ON T.user_id = U.id
            LEFT JOIN hr_employee EMP ON EMP.user_id = U.id AND T.company_id = EMP.company_id
            LEFT JOIN hr_department DEP ON EMP.department_id = DEP.id
        """
        return from_str
