# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class hr_department(models.Model):
    _inherit = 'hr.department'

    def _get_default_appraisal_survey_template_id(self):
        return self.env.company.appraisal_survey_template_id

    appraisal_survey_template_id = fields.Many2one('survey.survey', string='Appraisal Survey',
        domain=[('survey_type', '=', 'appraisal')], default=_get_default_appraisal_survey_template_id,
        help='This field is used with 360 Feedback setting on Appraisal App, the aim is to define a default Survey Template related to this department.'
    )
