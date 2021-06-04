# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    module_website_hr_recruitment = fields.Boolean(string='Online Posting')
    module_hr_recruitment_survey = fields.Boolean(string='Interview Forms')
    refuse_existing_applications = fields.Boolean(related="company_id.refuse_existing_applications", readonly=False)
    module_hr_recruitment_skills = fields.Boolean(string='Manage Applicant Skills')
