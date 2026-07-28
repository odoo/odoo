# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _inherit = ['calendar.recurrence', 'microsoft.calendar.sync']


    # Don't sync by default. Sync only when the recurrence is applied
    need_sync_m = fields.Boolean(default=False)

    microsoft_id = fields.Char('Microsoft Calendar Recurrence Id')

    def _compute_rrule(self):
        # Note: 'need_sync_m' is set to False to avoid syncing the updated recurrence with
        # Outlook, as this update may already come from Outlook. If not, this modification will
        # be already synced through the calendar.event.write()
        for recurrence in self:
            if recurrence.rrule != recurrence._rrule_serialize():
                recurrence.write({'rrule': recurrence._rrule_serialize()})

    def _inverse_rrule(self):
        # Note: 'need_sync_m' is set to False to avoid syncing the updated recurrence with
        # Outlook, as this update mainly comes from Outlook (the 'rrule' field is not directly
        # modified in Odoo but computed from other fields).
        for recurrence in self.filtered('rrule'):
            values = self._rrule_parse(recurrence.rrule, recurrence.dtstart)
            recurrence.with_context(dont_notify=True).write(dict(values, need_sync_m=False))

    def _apply_recurrence(self, specific_values_creation=None, no_send_edit=False, generic_values_creation=None):
        events = self.filtered('need_sync_m').calendar_event_ids
        detached_events = super()._apply_recurrence(specific_values_creation, no_send_edit, generic_values_creation)

        # If a synced event becomes a recurrence, the event needs to be deleted from
        # Microsoft since it's now the recurrence which is synced.
        vals = []
        for event in events._get_synced_events():
            if event.active and event.ms_universal_event_id and not event.recurrence_id.ms_universal_event_id:
                vals += [{
                    'name': event.name,
                    'microsoft_id': event.microsoft_id,
                    'start': event.start,
                    'stop': event.stop,
                    'active': False,
                    'need_sync_m': True,
                }]
                event._microsoft_delete(event.user_id, event.ms_organizer_event_id)
                event.ms_universal_event_id = False
        self.env['calendar.event'].create(vals)
        self.calendar_event_ids.need_sync_m = False
        return detached_events

    def _write_events(self, values, dtstart=None):
        # If only some events are updated, sync those events.
        # If all events are updated, sync the recurrence instead.
        values['need_sync_m'] = bool(dtstart) or values.get("need_sync_m", True)
        return super()._write_events(values, dtstart=dtstart)

    def _get_organizer(self):
        return self.base_event_id.user_id

    def _get_rrule(self, dtstart=None):
        if not dtstart and self.dtstart:
            dtstart = self.dtstart
        return super()._get_rrule(dtstart)

    def _get_microsoft_synced_fields(self):
        return {'rrule'} | self.env['calendar.event']._get_microsoft_synced_fields()

    @api.model
    def _restart_microsoft_sync(self):
        self.env['calendar.recurrence'].search(self._get_microsoft_sync_domain()).write({
            'need_sync_m': True,
        })

    def _has_base_event_time_fields_changed(self, new):
        """
        Indicates if at least one time field of the base event has changed, based
        on provided `new` values.
        Note: for all day event comparison, hours/minutes are ignored.
        """
        def _convert(value, to_convert):
            return value.date() if to_convert else value

        old = self.base_event_id and self.base_event_id.read(['start', 'stop', 'allday'])[0]
        return old and (
            old['allday'] != new['allday']
            or any(
                _convert(new[f], new['allday']) != _convert(old[f], old['allday'])
                for f in ('start', 'stop')
            )
        )

    def _write_from_microsoft(self, microsoft_event, vals):
        current_rrule = self.rrule
        # event_tz is written on event in Microsoft but on recurrence in Odoo
        vals['event_tz'] = microsoft_event.start.get('timeZone')
        super()._write_from_microsoft(microsoft_event, vals)
        new_event_values = self.env["calendar.event"]._microsoft_to_odoo_values(microsoft_event)
        # Edge case:  if the base event was deleted manually in 'self_only' update, skip applying recurrence.
        if self._has_base_event_time_fields_changed(new_event_values) and (new_event_values['start'] >= self.base_event_id.start):
            # we need to recreate the recurrence, time_fields were modified.
            base_event_id = self.base_event_id
            # We archive the old events to recompute the recurrence. These events are already deleted on Microsoft side.
            # We can't call _cancel because events without user_id would not be deleted
            (self.calendar_event_ids - base_event_id).microsoft_id = False
            (self.calendar_event_ids - base_event_id).unlink()
            base_event_id.with_context(dont_notify=True).write(dict(
                new_event_values, microsoft_id=False, need_sync_m=False
            ))
            if self.rrule == current_rrule:
                # if the rrule has changed, it will be recalculated below
                # There is no detached event now
                self.with_context(dont_notify=True)._apply_recurrence()
        else:
            time_fields = (
                    self.env["calendar.event"]._get_time_fields()
                    | self.env["calendar.event"]._get_recurrent_fields()
            )
            # We avoid to write time_fields because they are not shared between events.
            self.with_context(dont_notify=True)._write_events(dict({
                field: value
                for field, value in new_event_values.items()
                if field not in time_fields
                }, need_sync_m=False)
            )
        # We apply the rrule check after the time_field check because the microsoft ids are generated according
        # to base_event start datetime.
        if self.rrule != current_rrule:
            detached_events = self._apply_recurrence()
            detached_events.microsoft_id = False
            detached_events.unlink()

    def _get_microsoft_sync_domain(self):
        # Do not sync Odoo recurrences with Outlook Calendar anymore.
        domain = expression.FALSE_DOMAIN
        return self._extend_microsoft_domain(domain)

    def _cancel_microsoft(self):
        self.calendar_event_ids.with_context(dont_notify=True)._cancel_microsoft()
        super()._cancel_microsoft()

    @api.model
    def _microsoft_to_odoo_values(self, microsoft_recurrence, default_reminders=(), default_values=None, with_ids=False):
        recurrence = microsoft_recurrence.get_recurrence()

        if with_ids:
            recurrence = {
                **recurrence,
                'ms_organizer_event_id': microsoft_recurrence.id,
                'ms_universal_event_id': microsoft_recurrence.iCalUId,
            }

        return recurrence

    def _microsoft_values(self, fields_to_sync):
        """
        Get values to update the whole Outlook event recurrence.
        (done through the first event of the Outlook recurrence).
        """
        return self.base_event_id._microsoft_values(fields_to_sync, initial_values={'type': 'seriesMaster'})

    def _ensure_attendees_have_email(self):
        self.calendar_event_ids.filtered(lambda e: e.active)._ensure_attendees_have_email()

    def _split_from(self, event, recurrence_values=None):
        """
        When a recurrence is splitted, the base event of the new recurrence already
        exist and may be already synced with Outlook.
        In this case, we need to be removed this event on Outlook side to avoid duplicates while posting
        the new recurrence.
        """
        new_recurrence = super()._split_from(event, recurrence_values)
        if new_recurrence and new_recurrence.base_event_id.microsoft_id:
            new_recurrence.base_event_id._microsoft_delete(
                new_recurrence.base_event_id._get_organizer(),
                new_recurrence.base_event_id.ms_organizer_event_id
            )

        return new_recurrence

    def _get_event_user_m(self, user_id=None):
        """ Get the user who will send the request to Microsoft (organizer if synchronized and current user otherwise). """
        self.ensure_one()
        event = self._get_first_event()
        if event:
            return event._get_event_user_m(user_id)
        return self.env.user
