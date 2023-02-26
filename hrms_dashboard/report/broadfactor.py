# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo import tools
from odoo import api, fields, models


class EmployeeBroadFactor(models.Model):
    _name = "hr.employee.broad.factor"
    _description = "Employee Broadfactor"
    _auto = False

    name = fields.Char()
    no_of_occurrence = fields.Integer()
    no_of_days = fields.Integer()
    broad_factor = fields.Integer()

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_employee_broad_factor')
        date_today = date.today()
        self._cr.execute("""
            create or replace view hr_employee_broad_factor as (
                select
                    e.id,
                    e.name, 
                    count(h.*) as no_of_occurrence,
                    sum(h.number_of_days) as no_of_days,
                    count(h.*)*count(h.*)*sum(h.number_of_days) as broad_factor
                from hr_employee e
                    full join (select * from hr_leave where state = 'validate' and date_to <= now()::timestamp) h
                    on e.id =h.employee_id
                group by e.id
               )""")


class ReportOverdue(models.AbstractModel):
    _name = 'report.hrms_dashboard.report_broadfactor'

    @api.model
    def get_report_values(self, docids=None, data=None):
        sql = """select * from hr_employee_broad_factor"""
        self.env.cr.execute(sql)
        lines = self.env.cr.dictfetchall()
        return {
            'doc_model': 'hr.employee.broad_factor',
            'lines': lines,
            'Date': fields.date.today(),
        }
