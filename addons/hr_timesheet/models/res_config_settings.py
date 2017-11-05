# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_timesheet_synchro = fields.Boolean("Awesome Timesheet")
    module_sale_timesheet = fields.Boolean("Time Billing")
    module_project_timesheet_holidays = fields.Boolean("Leaves")
