# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_country_code = fields.Char(related='company_id.country_id.code', string='Company Country Code')
    time_off_reference_calendar = fields.Many2one(
        'resource.calendar', string='Reference Calendar',
        related='company_id.time_off_reference_calendar', readonly=False)
