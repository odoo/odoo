# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    oe_update_date = fields.Datetime(string='Odoo Update Date')

    @api.multi
    def write(self, vals):
        sync_fields = set(self.get_fields_need_update_google())
        if (set(vals.keys()) & sync_fields) and 'oe_update_date' not in vals.keys() and 'NewMeeting' not in self.env.context:
            vals['oe_update_date'] = fields.Datetime.now()

        return super(CalendarEvent, self).write(vals)

    @api.multi
    def unlink(self, can_be_deleted=False):
        return super(CalendarEvent, self).unlink(can_be_deleted=can_be_deleted)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if default.get('write_type'):
            del default['write_type']
        elif default.get('recurrent_id'):
            default['oe_update_date'] = fields.Datetime.now()
        else:
            default['oe_update_date'] = False
        return super(CalendarEvent, self).copy(default)

    def get_fields_need_update_google(self):
        recurrent_fields = self._get_recurrent_fields()
        return recurrent_fields + ['name', 'description', 'allday', 'start', 'date_end', 'stop',
                'attendee_ids', 'alarm_ids', 'location', 'class', 'active',
                'start_date', 'start_datetime', 'stop_date', 'stop_datetime']
