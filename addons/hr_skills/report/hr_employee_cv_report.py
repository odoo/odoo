# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportHr_SkillsReport_Employee_Cv(models.AbstractModel):
    _name = 'report.hr_skills.report_employee_cv'
    _description = 'Employee Resume'

    def _get_report_values(self, docids, data=None):
        show_others = (data or {}).get('show_others')
        employees = self.env['hr.employee'].browse(docids)

        resume_lines = {}
        for employee in employees:
            filtered_lines = employee.resume_line_ids.filtered(lambda l: show_others or l.line_type_id)
            resume_lines[employee] = filtered_lines.grouped(lambda l: l.line_type_id.name or l.env._("Other"))
        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee',
            'docs': employees,
            'resume_lines': resume_lines,
        }
