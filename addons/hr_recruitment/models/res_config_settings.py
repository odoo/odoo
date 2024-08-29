# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    module_website_hr_recruitment = fields.Boolean(string='Online Posting')
    module_hr_recruitment_survey = fields.Boolean(string='Interview Forms')
    group_applicant_cv_display = fields.Boolean(implied_group="hr_recruitment.group_applicant_cv_display")
    module_hr_recruitment_extract = fields.Boolean(string='Send CV to OCR to fill applications')
