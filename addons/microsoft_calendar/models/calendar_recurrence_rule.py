# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _inherit = ['calendar.recurrence', 'microsoft.calendar.sync']


    # Don't sync by default. Sync only when the recurrence is applied
    need_sync_m = fields.Boolean(default=False)

    microsoft_id = fields.Char('Microsoft Calendar Recurrence Id')

    def _apply_recurrence(self, specific_values_creation=None, no_send_edit=False):
        events = self.calendar_event_ids
        detached_events = super()._apply_recurrence(specific_values_creation, no_send_edit)

        microsoft_service = MicrosoftCalendarService(self.env['microsoft.service'])

        # If a synced event becomes a recurrence, the event needs to be deleted from
        # Microsoft since it's now the recurrence which is synced.
        # Those events are kept in the database and their microsoft_id is updated
        # according to the recurrence microsoft_id, therefore we need to keep an inactive copy
        # of those events with the original microsoft_id. The next sync will then correctly
        # delete those events from Microsoft.
        vals = []
        for event in events.filtered('microsoft_id'):
            if event.active and event.microsoft_id and not event.recurrence_id.microsoft_id:
                vals += [{
                    'name': event.name,
                    'microsoft_id': event.microsoft_id,
                    'start': event.start,
                    'stop': event.stop,
                    'active': False,
                    'need_sync_m': True,
                }]
                event._microsoft_delete(microsoft_service, event.microsoft_id)
                event.microsoft_id = False
        self.env['calendar.event'].create(vals)

        if not no_send_edit:
            for recurrence in self:
                values = recurrence._microsoft_values(self._get_microsoft_synced_fields())
                if not values:
                    continue
                values = values[0]
                if not recurrence.microsoft_id:
                    recurrence._microsoft_insert(microsoft_service, values)
                else:
                    recurrence._microsoft_patch(microsoft_service, recurrence.microsoft_id, values)

        self.calendar_event_ids.need_sync_m = False
        return detached_events

    def _write_events(self, values, dtstart=None):
        # If only some events are updated, sync those events.
        # If all events are updated, sync the recurrence instead.
        values['need_sync_m'] = bool(dtstart)
        if not dtstart:
            self.need_sync_m = True
        return super()._write_events(values, dtstart=dtstart)

    def _get_microsoft_synced_fields(self):
        return {'rrule'} | self.env['calendar.event']._get_microsoft_synced_fields()

    def _get_microsoft_sync_domain(self):
        return [('calendar_event_ids.user_id', '=', self.env.user.id)]

    def _cancel_microsoft(self):
        self.calendar_event_ids._cancel_microsoft()
        self.microsoft_id = False  # Set to False to avoid error with unlink from microsoft and avoid to synchronize.
        self.unlink()

    @api.model
    def _microsoft_to_odoo_values(self, microsoft_recurrence, default_reminders=(), default_values={}):
        recurrence = microsoft_recurrence.get_recurrence()

        return {
            **recurrence,
            'microsoft_id': microsoft_recurrence.id,
        }

    def _microsoft_values(self, fields_to_sync):
        events = self.calendar_event_ids.sorted('start')
        events_outliers = self.calendar_event_ids.filtered(lambda e: not e.follow_recurrence)
        normal_event = (events - events_outliers)[:1] or events[:1]
        if not normal_event:
            return {}
        values = [normal_event._microsoft_values(fields_to_sync, initial_values={'type': 'seriesMaster'})]

        if self.microsoft_id:
            values[0]['id'] = self.microsoft_id
            for event in events_outliers:
                event_value = event._microsoft_values(fields_to_sync)
                values += [event_value]

        return values

    def _ensure_attendees_have_email(self):
        self.calendar_event_ids.filtered(lambda e: e.active)._ensure_attendees_have_email()

    def _notify_attendees(self):
        recurrences = self.filtered(
            lambda recurrence: recurrence.base_event_id.alarm_ids and (
                not recurrence.until or recurrence.until >= fields.Date.today() - relativedelta(days=1)
            ) and max(recurrence.calendar_event_ids.mapped('stop')) >= fields.Datetime.now()
        )
        partners = recurrences.base_event_id.partner_ids
        if partners:
            self.env['calendar.alarm_manager']._notify_next_alarm(partners.ids)
