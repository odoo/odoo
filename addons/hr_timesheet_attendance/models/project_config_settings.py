# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HrTimesheetConfiguration(models.TransientModel):
    _inherit = 'project.config.settings'

    timesheet_max_difference = fields.Float(related='company_id.timesheet_max_difference', string="Timesheet allowed difference(Hours) *")
