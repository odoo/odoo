# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class RecruitmentSettings(models.TransientModel):
    _name = 'hr.recruitment.config.settings'
    _inherit = ['res.config.settings']

    module_website_hr_recruitment = fields.Boolean(string='Online Posting')
    module_hr_recruitment_survey = fields.Boolean(string='Interview Forms')
    module_website_sign = fields.Boolean(string='eSign')
    module_hr_appraisal = fields.Boolean(string='Appraisals')
