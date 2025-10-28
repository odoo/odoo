# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, tools


class EmployeeBroadFactor(models.Model):
    """ For calculating employees broad factor(depend on the leaves)"""
    _name = "hr.employee.broad.factor"
    _description = "Employee Broadfactor"
    _auto = False

    name = fields.Char(string="Name", help="Name for the record")
    no_of_occurrence = fields.Integer(string="No.of Occurrence",
                                      help="No.of Occurrence")
    no_of_days = fields.Integer(string="No.of Days", help="No.of days")
    broad_factor = fields.Integer(string="Broad Factor", help="Broad factor")

    def init(self):
        """Calculate broad factor that depends on employee leaves"""
        tools.drop_view_if_exists(self._cr, 'hr_employee_broad_factor')
        self._cr.execute("""
            create or replace view hr_employee_broad_factor as (
                select
                    e.id, e.name, count(h.*) as no_of_occurrence,
                    sum(h.number_of_days) as no_of_days,
                    count(h.*)*count(h.*)*sum(h.number_of_days) as broad_factor
                from hr_employee e
                    full join (select * from hr_leave where state = 'validate' 
                    and date_to <= now()::timestamp) h
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
