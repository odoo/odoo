# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    hr_recruitment_indeed_client_id = fields.Char(related="company_id.hr_recruitment_indeed_client_id", readonly=False)
    hr_recruitment_indeed_secret = fields.Char(related="company_id.hr_recruitment_indeed_secret", readonly=False)
