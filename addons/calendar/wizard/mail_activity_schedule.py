# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    calendar_event_id = fields.Many2one(related='activity_id.calendar_event_id')

    def action_create_calendar_event(self):
        self.ensure_one()
        if self.is_batch_mode:
            raise UserError(_("Scheduling an activity using the calendar is not possible on more than one record."))
        return self.with_context({
            'default_res_model': self.res_model,
            'default_res_id': self._get_converted_res_ids()[0],
        })._action_schedule_activities().action_create_calendar_event()

    def _add_errors_plan(self, errors, applied_on):
        super()._add_errors_plan(errors, applied_on)
        if self.activity_category in ('meeting', 'phonecall') and self.is_batch_mode:
            errors.add(_('Meetings and phone calls cannot be created in batch mode. Please select only one record.'))

    @api.depends('activity_category')
    def _compute_error(self):
        super()._compute_error()
