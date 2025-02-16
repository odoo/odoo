# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrResumeLine(models.Model):
    _name = 'hr.resume.line'
    _description = "Resume line of an employee"
    _order = "line_type_id, date_end desc, date_start desc"

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True, translate=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date()
    description = fields.Html(string="Description", translate=True)
    line_type_id = fields.Many2one('hr.resume.line.type', string="Type")
    is_survey_visible = fields.Boolean(string='Is Survey Visible', compute='_compute_is_survey_visible')
    is_social_media = fields.Boolean(string='Is Social Media Category', compute='_compute_is_social_media')
    profile = fields.Char(string='Profile')

    # Used to apply specific template on a line
    display_type = fields.Selection([('classic', 'Classic'), ('certification', 'Certification')], string="Display", default='classic')

    _date_check = models.Constraint(
        'CHECK ((date_start <= date_end OR date_end IS NULL))',
        'The start date must be anterior to the end date.',
    )

    @api.depends('line_type_id.name', 'display_type')
    def _compute_is_survey_visible(self):
        internal_certification_type = self.env.ref('hr_skills_survey.resume_type_certification', False)
        for line in self:
            if internal_certification_type and line.line_type_id == internal_certification_type and line.display_type == 'certification':
                line.is_survey_visible = True
            else:
                line.is_survey_visible = False

    @api.depends('line_type_id')
    def _compute_is_social_media(self):
        social_media_type = self.env.ref('hr_skills.resume_type_social_media', False)
        for line in self:
            if line.line_type_id == social_media_type:
                line.is_social_media = True
            else:
                line.is_social_media = False
