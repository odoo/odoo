# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Datetime


class BaseAutomation(models.Model):
    """ Add resource and calendar for time-based conditions """
    _inherit = 'base.automation'

    trg_date_resource_field_id = fields.Many2one('ir.model.fields', string='Use employee work schedule', help='Use the user\'s working schedule.')

    @api.model
    def _get_calendar(self, automation, record):
        if automation.trg_date_range_type == 'day' and automation.trg_date_resource_field_id:
            user = record[automation.trg_date_resource_field_id.name]
            calendar = user.employee_id.contract_id.resource_calendar_id
            if calendar:
                return calendar
        return super()._get_calendar(automation, record)
