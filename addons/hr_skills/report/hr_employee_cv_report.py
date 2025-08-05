# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models


# DONE
class ReportHr_SkillsReport_Employee_Cv(models.AbstractModel):
    _name = 'report.hr_skills.report_employee_cv'
    _description = 'Employee Resume'

    def _get_report_values(self, docids, data=None):
        show_others = (data or {}).get('show_others')
        employees = self.env['hr.employee'].browse(docids)

        resume_lines = {}
        for employee in employees:
            resume_lines[employee] = defaultdict(self.env['hr.resume.line'].browse)
            for line in employee.resume_line_ids:
                if not show_others and not line.line_type_id:
                    continue
                resume_lines[employee][line.line_type_id.name or _('Other')] |= line

        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee',
            'docs': employees,
            'resume_lines': resume_lines,
        }
