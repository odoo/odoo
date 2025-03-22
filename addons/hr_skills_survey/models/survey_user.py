# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
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
        partner_has_completed = {user_input.partner_id.id: user_input.survey_id for user_input in certification_user_inputs}
        employees = self.env['hr.employee'].sudo().search([('user_id.partner_id', 'in', certification_user_inputs.mapped('partner_id').ids)])
        for employee in employees:
            line_type = self.env.ref('hr_skills_survey.resume_type_certification', raise_if_not_found=False)
            survey = partner_has_completed.get(employee.user_id.partner_id.id)
            self.env['hr.resume.line'].create({
                'employee_id': employee.id,
                'name': survey.title,
                'date_start': fields.Date.today(),
                'date_end': fields.Date.today(),
                'description': html2plaintext(survey.description) if survey.description else '',
                'line_type_id': line_type and line_type.id,
                'display_type': 'certification',
                'survey_id': survey.id
            })


class ResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    display_type = fields.Selection(selection_add=[('certification', 'Certification')])
    survey_id = fields.Many2one('survey.survey', string='Certification', readonly=True)
