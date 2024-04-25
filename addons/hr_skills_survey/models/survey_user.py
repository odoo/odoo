# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.osv import expression
from odoo.tools import html2plaintext


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _mark_done(self):
        """ Will add certification to employee's resume if
        - The survey is a certification
        - The user is linked to an employee
        - The user succeeded the test """

        super(SurveyUserInput, self)._mark_done()

        certification_user_inputs = self.filtered(lambda user_input: user_input.survey_id.certification and user_input.scoring_success)
        user_inputs_by_partner = certification_user_inputs.grouped('partner_id')
        employees = self.env['hr.employee'].search(
            [('user_id.partner_id', 'in', certification_user_inputs.partner_id.ids)])
        resume_lines = self.env['hr.resume.line'].search(
            expression.OR([
                expression.AND([
                    [('employee_id', '=', employee.id)],
                    [('survey_id', 'in', user_inputs_by_partner[employee.user_id.partner_id].survey_id.ids)]])
                for employee in employees
            ]))
        resume_survey_by_ids = resume_lines.grouped(
            lambda resume_line: (resume_line.employee_id, resume_line.survey_id))
        line_type = self.env.ref('hr_skills_survey.resume_type_certification', raise_if_not_found=False)

        lines_to_create = []
        today = fields.Date.today()
        for employee in employees:
            for user_input in user_inputs_by_partner[employee.user_id.partner_id]:
                survey = user_input.survey_id
                date_start = today
                validity_month = survey.certification_validity_months
                resume_line_vals = {
                    'employee_id': employee.id,
                    'name': survey.title,
                    'date_start': date_start,
                    'date_end': date_start + relativedelta(months=validity_month) if validity_month else False,
                    'description': html2plaintext(survey.description),
                    'line_type_id': line_type.id if line_type else False,
                    'display_type': 'certification',
                    'survey_id': survey.id,
                }
                if existing_resume_survey := resume_survey_by_ids.get((employee, survey)):
                    existing_resume_survey.write(resume_line_vals)
                else:
                    lines_to_create.append(resume_line_vals)
        self.env['hr.resume.line'].create(lines_to_create)
