# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Datetime


class BaseActionRule(models.Model):
    """ Add resource and calendar for time-based conditions """

    _inherit = 'base.action.rule'

    trg_date_resource_field_id = fields.Many2one('ir.model.fields', string='Use employee work schedule', help='Use the user\'s working schedule.')

    @api.model
    def _check_delay(self, action, record, record_dt):
        """ Override the check of delay to try to use a user-related calendar.
            If no calendar is found, fallback on the default behavior.
        """
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day' and action.trg_date_resource_field_id:
            user = record[action.trg_date_resource_field_id.name]
            if user.employee_ids and user.employee_ids[0].contract_id and user.employee_ids[0].contract_id.working_hours:
                calendar = user.employee_ids[0].contract_id.working_hours
                start_dt = Datetime.from_string(record_dt)
                resource_id = user.employee_ids[0].resource_id.id
                return calendar.schedule_days_get_date(action.trg_date_range, day_date=start_dt, compute_leaves=True, resource_id=resource_id)
        return super(BaseActionRule, self)._check_delay(action, record, record_dt)
