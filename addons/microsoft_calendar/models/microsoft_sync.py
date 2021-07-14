# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from contextlib import contextmanager
from functools import wraps
import requests
import pytz
from dateutil.parser import parse

from odoo import api, fields, models, registry, _
from odoo.tools import ormcache_context
from odoo.exceptions import UserError
from odoo.osv import expression

from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_account.models.microsoft_service import TIMEOUT

_logger = logging.getLogger(__name__)

MAX_RECURRENT_EVENT = 720


# API requests are sent to Microsoft Calendar after the current transaction ends.
# This ensures changes are sent to Microsoft only if they really happened in the Odoo database.
# It is particularly important for event creation , otherwise the event might be created
# twice in Microsoft if the first creation crashed in Odoo.
def after_commit(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        dbname = self.env.cr.dbname
        context = self.env.context
        uid = self.env.uid

        @self.env.cr.postcommit.add
        def called_after():
            db_registry = registry(dbname)
            with api.Environment.manage(), db_registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                try:
                    func(self.with_env(env), *args, **kwargs)
                except Exception as e:
                    _logger.warning("Could not sync record now: %s" % self)
                    _logger.exception(e)

    return wrapped

@contextmanager
def microsoft_calendar_token(user):
    try:
        yield user._get_microsoft_calendar_token()
    except requests.HTTPError as e:
        if e.response.status_code == 401:  # Invalid token.
            # The transaction should be rolledback, but the user's tokens
            # should be reset. The user will be asked to authenticate again next time.
            # Rollback manually first to avoid concurrent access errors/deadlocks.
            user.env.cr.rollback()
            with user.pool.cursor() as cr:
                env = user.env(cr=cr)
                user.with_env(env)._set_microsoft_auth_tokens(False, False, 0)
        raise e

class MicrosoftSync(models.AbstractModel):
    _name = 'microsoft.calendar.sync'
    _description = "Synchronize a record with Microsoft Calendar"

    microsoft_id = fields.Char('Microsoft Calendar Id', copy=False)
    need_sync_m = fields.Boolean(default=True, copy=False)
    active = fields.Boolean(default=True)

    def write(self, vals):
        microsoft_service = MicrosoftCalendarService(self.env['microsoft.service'])
        if 'microsoft_id' in vals:
            self._from_microsoft_ids.clear_cache(self)
        synced_fields = self._get_microsoft_synced_fields()
        if 'need_sync_m' not in vals and vals.keys() & synced_fields:
            fields_to_sync = [x for x in vals.keys() if x in synced_fields]
            if fields_to_sync:
                vals['need_sync_m'] = True
        else:
            fields_to_sync = [x for x in vals.keys() if x in synced_fields]

        result = super().write(vals)
        for record in self.filtered('need_sync_m'):
            if record.microsoft_id and fields_to_sync:
                values = record._microsoft_values(fields_to_sync)
                if not values:
                    continue
                record._microsoft_patch(microsoft_service, record.microsoft_id, values, timeout=3)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('microsoft_id') for vals in vals_list):
            self._from_microsoft_ids.clear_cache(self)
        records = super().create(vals_list)

        microsoft_service = MicrosoftCalendarService(self.env['microsoft.service'])
        records_to_sync = records.filtered(lambda r: r.need_sync_m and r.active)
        for record in records_to_sync:
            record._microsoft_insert(microsoft_service, record._microsoft_values(self._get_microsoft_synced_fields()), timeout=3)
        return records

    def unlink(self):
        """We can't delete an event that is also in Microsoft Calendar. Otherwise we would
        have no clue that the event must must deleted from Microsoft Calendar at the next sync.
        """
        synced = self.filtered('microsoft_id')
        if self.env.context.get('archive_on_error') and self._active_name:
            synced.write({self._active_name: False})
            self = self - synced
        elif synced:
            raise UserError(_("You cannot delete a record synchronized with Outlook Calendar, archive it instead."))
        return super().unlink()

    @api.model
    @ormcache_context('microsoft_ids', keys=('active_test',))
    def _from_microsoft_ids(self, microsoft_ids):
        if not microsoft_ids:
            return self.browse()
        return self.search([('microsoft_id', 'in', microsoft_ids)])

    def _sync_odoo2microsoft(self, microsoft_service: MicrosoftCalendarService):
        if not self:
            return
        if self._active_name:
            records_to_sync = self.filtered(self._active_name)
        else:
            records_to_sync = self
        cancelled_records = self - records_to_sync

        records_to_sync._ensure_attendees_have_email()
        updated_records = records_to_sync.filtered('microsoft_id')
        new_records = records_to_sync - updated_records
        for record in cancelled_records.filtered('microsoft_id'):
            record._microsoft_delete(microsoft_service, record.microsoft_id)
        for record in new_records:
            values = record._microsoft_values(self._get_microsoft_synced_fields())
            if isinstance(values, dict):
                record._microsoft_insert(microsoft_service, values)
            else:
                for value in values:
                    record._microsoft_insert(microsoft_service, value)
        for record in updated_records:
            values = record._microsoft_values(self._get_microsoft_synced_fields())
            if not values:
                continue
            record._microsoft_patch(microsoft_service, record.microsoft_id, values)

    def _cancel_microsoft(self):
        self.microsoft_id = False
        self.unlink()

    def _sync_recurrence_microsoft2odoo(self, microsoft_events: MicrosoftEvent):
        recurrent_masters = microsoft_events.filter(lambda e: e.is_recurrence())
        recurrents = microsoft_events.filter(lambda e: e.is_recurrent_not_master())
        default_values = {'need_sync_m': False}

        new_recurrence = self.env['calendar.recurrence']

        for recurrent_master in recurrent_masters:
            new_calendar_recurrence = dict(self.env['calendar.recurrence']._microsoft_to_odoo_values(recurrent_master, (), default_values), need_sync_m=False)
            to_create = recurrents.filter(lambda e: e.seriesMasterId == new_calendar_recurrence['microsoft_id'])
            recurrents -= to_create
            base_values = dict(self.env['calendar.event']._microsoft_to_odoo_values(recurrent_master, (), default_values), need_sync_m=False)
            to_create_values = []
            if new_calendar_recurrence.get('end_type', False) in ['count', 'forever']:
                to_create = list(to_create)[:MAX_RECURRENT_EVENT]
            for recurrent_event in to_create:
                if recurrent_event.type == 'occurrence':
                    value = self.env['calendar.event']._microsoft_to_odoo_recurrence_values(recurrent_event, (), base_values)
                else:
                    value = self.env['calendar.event']._microsoft_to_odoo_values(recurrent_event, (), default_values)

                to_create_values += [dict(value, need_sync_m=False)]

            new_calendar_recurrence['calendar_event_ids'] = [(0, 0, to_create_value) for to_create_value in to_create_values]
            new_recurrence_odoo = self.env['calendar.recurrence'].create(new_calendar_recurrence)
            new_recurrence_odoo.base_event_id = new_recurrence_odoo.calendar_event_ids[0] if new_recurrence_odoo.calendar_event_ids else False
            new_recurrence |= new_recurrence_odoo

        for recurrent_master_id in set([x.seriesMasterId for x in recurrents]):
            recurrence_id = self.env['calendar.recurrence'].search([('microsoft_id', '=', recurrent_master_id)])
            to_update = recurrents.filter(lambda e: e.seriesMasterId == recurrent_master_id)
            for recurrent_event in to_update:
                if recurrent_event.type == 'occurrence':
                    value = self.env['calendar.event']._microsoft_to_odoo_recurrence_values(recurrent_event, (), {'need_sync_m': False})
                else:
                    value = self.env['calendar.event']._microsoft_to_odoo_values(recurrent_event, (), default_values)
                existing_event = recurrence_id.calendar_event_ids.filtered(lambda e: e._range() == (value['start'], value['stop']))
                if not existing_event:
                    continue
                value.pop('start')
                value.pop('stop')
                existing_event.write(value)
            new_recurrence |= recurrence_id
        return new_recurrence

    def _update_microsoft_recurrence(self, recurrence_event, events):
        vals = dict(self.base_event_id._microsoft_to_odoo_values(recurrence_event, ()), need_sync_m=False)
        vals['microsoft_recurrence_master_id'] = vals.pop('microsoft_id')
        self.base_event_id.write(vals)
        values = {}
        default_values = {}

        normal_events = []
        events_to_update = events.filter(lambda e: e.seriesMasterId == self.microsoft_id)
        if self.end_type in ['count', 'forever']:
            events_to_update = list(events_to_update)[:MAX_RECURRENT_EVENT]

        for recurrent_event in events_to_update:
            if recurrent_event.type == 'occurrence':
                value = self.env['calendar.event']._microsoft_to_odoo_recurrence_values(recurrent_event, (), default_values)
                normal_events += [recurrent_event.odoo_id(self.env)]
            else:
                value = self.env['calendar.event']._microsoft_to_odoo_values(recurrent_event, (), default_values)
                self.env['calendar.event'].browse(recurrent_event.odoo_id(self.env)).with_context(no_mail_to_attendees=True, mail_create_nolog=True).write(dict(value, need_sync_m=False))
            if value.get('start') and value.get('stop'):
                values[(self.id, value.get('start'), value.get('stop'))] = dict(value, need_sync_m=False)

        if (self.id, vals.get('start'), vals.get('stop')) in values:
            base_event_vals = dict(vals)
            base_event_vals.update(values[(self.id, vals.get('start'), vals.get('stop'))])
            self.base_event_id.write(base_event_vals)

        old_record = self._apply_recurrence(specific_values_creation=values, no_send_edit=True)

        vals.pop('microsoft_id', None)
        vals.pop('start', None)
        vals.pop('stop', None)
        normal_events = [e for e in normal_events if e in self.calendar_event_ids.ids]
        normal_event_ids = self.env['calendar.event'].browse(normal_events) - old_record
        if normal_event_ids:
            vals['follow_recurrence'] = True
            (self.env['calendar.event'].browse(normal_events) - old_record).write(vals)

        old_record._cancel_microsoft()
        if not self.base_event_id:
            self.base_event_id = self._get_first_event(include_outliers=False)

    @api.model
    def _sync_microsoft2odoo(self, microsoft_events: MicrosoftEvent, default_reminders=()):
        """Synchronize Microsoft recurrences in Odoo. Creates new recurrences, updates
        existing ones.

        :return: synchronized odoo
        """
        existing = microsoft_events.exists(self.env)
        new = microsoft_events - existing - microsoft_events.cancelled()
        new_recurrent = new.filter(lambda e: e.is_recurrent())

        default_values = {}

        odoo_values = [
            dict(self._microsoft_to_odoo_values(e, default_reminders, default_values), need_sync_m=False)
            for e in (new - new_recurrent)
        ]
        new_odoo = self.with_context(dont_notify=True).create(odoo_values)

        synced_recurrent_records = self.with_context(dont_notify=True)._sync_recurrence_microsoft2odoo(new_recurrent)
        if not self._context.get("dont_notify"):
            new_odoo._notify_attendees()
            synced_recurrent_records._notify_attendees()

        cancelled = existing.cancelled()
        cancelled_odoo = self.browse(cancelled.odoo_ids(self.env))
        cancelled_odoo._cancel_microsoft()

        recurrent_cancelled = self.env['calendar.recurrence'].search([
            ('microsoft_id', 'in', (microsoft_events.cancelled() - cancelled).microsoft_ids())])
        recurrent_cancelled._cancel_microsoft()

        synced_records = new_odoo + cancelled_odoo + synced_recurrent_records.calendar_event_ids

        for mevent in (existing - cancelled).filter(lambda e: e.lastModifiedDateTime and not e.seriesMasterId):
            # Last updated wins.
            # This could be dangerous if microsoft server time and odoo server time are different
            if mevent.is_recurrence():
                odoo_record = self.env['calendar.recurrence'].browse(mevent.odoo_id(self.env))
            else:
                odoo_record = self.browse(mevent.odoo_id(self.env))
            odoo_record_updated = pytz.utc.localize(odoo_record.write_date)
            updated = parse(mevent.lastModifiedDateTime or str(odoo_record_updated))
            if updated >= odoo_record_updated:
                vals = dict(odoo_record._microsoft_to_odoo_values(mevent, default_reminders), need_sync_m=False)
                odoo_record.write(vals)
                if odoo_record._name == 'calendar.recurrence':
                    odoo_record._update_microsoft_recurrence(mevent, microsoft_events)
                    synced_recurrent_records |= odoo_record
                else:
                    synced_records |= odoo_record

        return synced_records, synced_recurrent_records

    @after_commit
    def _microsoft_delete(self, microsoft_service: MicrosoftCalendarService, microsoft_id, timeout=TIMEOUT):
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if token:
                microsoft_service.delete(microsoft_id, token=token, timeout=timeout)

    @after_commit
    def _microsoft_patch(self, microsoft_service: MicrosoftCalendarService, microsoft_id, values, timeout=TIMEOUT):
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if token:
                self._ensure_attendees_have_email()
                microsoft_service.patch(microsoft_id, values, token=token, timeout=timeout)
                self.need_sync_m = False

    @after_commit
    def _microsoft_insert(self, microsoft_service: MicrosoftCalendarService, values, timeout=TIMEOUT):
        if not values:
            return
        with microsoft_calendar_token(self.env.user.sudo()) as token:
            if token:
                self._ensure_attendees_have_email()
                microsoft_id = microsoft_service.insert(values, token=token, timeout=timeout)
                self.write({
                    'microsoft_id': microsoft_id,
                    'need_sync_m': False,
                })

    def _get_microsoft_records_to_sync(self, full_sync=False):
        """Return records that should be synced from Odoo to Microsoft

        :param full_sync: If True, all events attended by the user are returned
        :return: events
        """
        domain = self._get_microsoft_sync_domain()
        if not full_sync:
            is_active_clause = (self._active_name, '=', True) if self._active_name else expression.TRUE_LEAF
            domain = expression.AND([domain, [
                '|',
                    '&', ('microsoft_id', '=', False), is_active_clause,
                    ('need_sync_m', '=', True),
            ]])
        return self.with_context(active_test=False).search(domain)

    @api.model
    def _microsoft_to_odoo_values(self, microsoft_event: MicrosoftEvent, default_reminders=()):
        """Implements this method to return a dict of Odoo values corresponding
        to the Microsoft event given as parameter
        :return: dict of Odoo formatted values
        """
        raise NotImplementedError()

    def _microsoft_values(self, fields_to_sync):
        """Implements this method to return a dict with values formatted
        according to the Microsoft Calendar API
        :return: dict of Microsoft formatted values
        """
        raise NotImplementedError()

    def _ensure_attendees_have_email(self):
        raise NotImplementedError()

    def _get_microsoft_sync_domain(self):
        """Return a domain used to search records to synchronize.
        e.g. return a domain to synchronize records owned by the current user.
        """
        raise NotImplementedError()

    def _get_microsoft_synced_fields(self):
        """Return a set of field names. Changing one of these fields
        marks the record to be re-synchronized.
        """
        raise NotImplementedError()

    def _notify_attendees(self):
        """ Notify calendar event partners.
        This is called when creating new calendar events in _sync_microsoft2odoo.
        At the initialization of a synced calendar, Odoo requests all events for a specific
        MicrosoftCalendar. Among those there will probably be lots of events that will never triggers a notification
        (e.g. single events that occured in the past). Processing all these events through the notification procedure
        of calendar.event.create is a possible performance bottleneck. This method aimed at alleviating that.
        """
        raise NotImplementedError()
