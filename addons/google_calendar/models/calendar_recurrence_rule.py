# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _inherit = ['calendar.recurrence', 'google.calendar.sync']


    # Don't sync by default. Sync only when the recurrence is applied
    need_sync = fields.Boolean(default=False)

    def _apply_recurrence(self, specific_values_creation=None, no_send_edit=False):
        events = self.calendar_event_ids
        detached_events = super()._apply_recurrence(specific_values_creation, no_send_edit)

        google_service = GoogleCalendarService(self.env['google.service'])

        # If a synced event becomes a recurrence, the event needs to be deleted from
        # Google since it's now the recurrence which is synced.
        # Those events are kept in the database and their google_id is updated
        # according to the recurrence google_id, therefore we need to keep an inactive copy
        # of those events with the original google id. The next sync will then correctly
        # delete those events from Google.
        vals = []
        for event in events.filtered('google_id'):
            if event.active and event.google_id != event.recurrence_id._get_event_google_id(event):
                vals += [{
                    'name': event.name,
                    'google_id': event.google_id,
                    'start': event.start,
                    'stop': event.stop,
                    'active': False,
                    'need_sync': True,
                }]
                event._google_delete(google_service, event.google_id)
                event.google_id = False
        self.env['calendar.event'].create(vals)

        for recurrence in self:
            values = recurrence._google_values()
            if not recurrence.google_id:
                recurrence._google_insert(google_service, values)
            else:
                recurrence._google_patch(google_service, recurrence.google_id, values)
        self.calendar_event_ids.need_sync = False
        return detached_events

    def _get_event_google_id(self, event):
        """Return the Google id of recurring event.
        Google ids of recurrence instances are formatted as: {recurrence google_id}_{UTC starting time in compacted ISO8601}
        """
        if self.google_id:
            if event.allday:
                time_id = event.start_date.isoformat().replace('-', '')
            else:
                # '-' and ':' are optional in ISO8601
                start_compacted_iso8601 = event.start.isoformat().replace('-', '').replace(':', '')
                # Z at the end for UTC
                time_id = '%sZ' % start_compacted_iso8601
            return '%s_%s' % (self.google_id, time_id)
        return False

    def _write_events(self, values, dtstart=None):
        values.pop('google_id', False)
        # If only some events are updated, sync those events.
        # If all events are updated, sync the recurrence instead.
        values['need_sync'] = bool(dtstart)
        if not dtstart:
            self.need_sync = True
        return super()._write_events(values, dtstart=dtstart)

    def _get_google_synced_fields(self):
        return {'rrule'}

    @api.model
    def _sync_google2odoo(self, *args, **kwargs):
        synced_recurrences = super()._sync_google2odoo(*args, **kwargs)
        detached_events = synced_recurrences._apply_recurrence()
        detached_events.unlink()
        return synced_recurrences

    def _get_sync_domain(self):
        return [('calendar_event_ids.user_id', '=', self.env.user.id)]

    @api.model
    def _odoo_values(self, google_recurrence, default_reminders=()):
        base_values = dict(self.env['calendar.event']._odoo_values(google_recurrence, default_reminders), need_sync=False)
        base_event = self.env['calendar.event'].create(base_values)
        return {
            'rrule': google_recurrence.rrule,
            'google_id': google_recurrence.id,
            'base_event_id': base_event.id,
            'calendar_event_ids': [(4, base_event.id)],
        }

    def _google_values(self):
        event = self._get_first_event()
        if not event:
            return {}
        values = event._google_values()
        values['id'] = self.google_id

        if not self._is_allday():
            values['start']['timeZone'] = self.event_tz
            values['end']['timeZone'] = self.event_tz

        # DTSTART is not allowed by Google Calendar API.
        # Event start and end times are specified in the start and end fields.
        rrule = re.sub('DTSTART:[0-9]{8}T[0-9]{1,8}\\n', '', self.rrule)
        values['recurrence'] = ['RRULE:%s' % rrule] if 'RRULE:' not in rrule else [rrule]
        values['extendedProperties'] = {
            'shared': {
                '%s_odoo_id' % self.env.cr.dbname: self.id,
            },
        }
        return values
