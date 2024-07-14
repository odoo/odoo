# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskSLAReport(models.Model):
    _inherit = 'helpdesk.sla.report.analysis'

    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += """, DEP.id as department_id,
                         EMP.parent_id as manager_id,
                         EMP.id as employee_id,
                         T.analytic_account_id as analytic_account_id"""
        return select_str

    def _group_by(self):
        return super()._group_by() + """ ,
            DEP.id,
            EMP.parent_id,
            EMP.id,
            T.analytic_account_id
        """

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN "res_users" U on T.user_id = U.id AND U.company_id = T.company_id
            LEFT JOIN "hr_employee" EMP on EMP.user_id = U.id AND EMP.company_id = T.company_id
            LEFT JOIN "hr_department" DEP on EMP.department_id = DEP.id AND DEP.company_id = T.company_id
        """
        return from_str
