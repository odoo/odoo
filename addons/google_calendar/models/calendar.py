# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Meeting(models.Model):

    _inherit = "calendar.event"

    oe_update_date = fields.Datetime('Odoo Update Date')

    @api.model
    def get_fields_need_update_google(self):
        recurrent_fields = self._get_recurrent_fields()
        return recurrent_fields + ['name', 'description', 'allday', 'start', 'date_end', 'stop',
                                   'attendee_ids', 'alarm_ids', 'location', 'privacy', 'active',
                                   'start_date', 'start_datetime', 'stop_date', 'stop_datetime']

    @api.multi
    def write(self, values):
        sync_fields = set(self.get_fields_need_update_google())
        if (set(values) and sync_fields) and 'oe_update_date' not in values and 'NewMeeting' not in self._context:
            if 'oe_update_date' in self._context:
                values['oe_update_date'] = self._context.get('oe_update_date')
            else:
                values['oe_update_date'] = fields.Datetime.now()
        return super(Meeting, self).write(values)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if default.get('write_type', False):
            del default['write_type']
        elif default.get('recurrent_id', False):
            default['oe_update_date'] = fields.Datetime.now()
        else:
            default['oe_update_date'] = False
        return super(Meeting, self).copy(default)

    @api.multi
    def unlink(self, can_be_deleted=False):
        return super(Meeting, self).unlink(can_be_deleted=can_be_deleted)


class Attendee(models.Model):

    _inherit = 'calendar.attendee'

    google_internal_event_id = fields.Char('Google Calendar Event Id')
    oe_synchro_date = fields.Datetime('Odoo Synchro Date')

    _sql_constraints = [
        ('google_id_uniq', 'unique(google_internal_event_id,partner_id,event_id)', 'Google ID should be unique!')
    ]

    @api.multi
    def write(self, values):
        for attendee in self:
            meeting_id_to_update = values.get('event_id', attendee.event_id.id)

            # If attendees are updated, we need to specify that next synchro need an action
            # Except if it come from an update_from_google
            if not self._context.get('curr_attendee', False) and not self._context.get('NewMeeting', False):
                self.env['calendar.event'].browse(meeting_id_to_update).write({'oe_update_date': fields.Datetime.now()})
        return super(Attendee, self).write(values)
