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

from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_account.models.google_service import TIMEOUT

_logger = logging.getLogger(__name__)


# API requests are sent to Google Calendar after the current transaction ends.
# This ensures changes are sent to Google only if they really happened in the Odoo database.
# It is particularly important for event creation , otherwise the event might be created
# twice in Google if the first creation crashed in Odoo.
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
def google_calendar_token(user):
    try:
        yield user._get_google_calendar_token()
    except requests.HTTPError as e:
        if e.response.status_code == 401:  # Invalid token.
            # The transaction should be rolledback, but the user's tokens
            # should be reset. The user will be asked to authenticate again next time.
            # Rollback manually first to avoid concurrent access errors/deadlocks.
            user.env.cr.rollback()
            with user.pool.cursor() as cr:
                env = user.env(cr=cr)
                user.with_env(env)._set_auth_tokens(False, False, 0)
        raise e

class GoogleSync(models.AbstractModel):
    _name = 'google.calendar.sync'
    _description = "Synchronize a record with Google Calendar"

    google_id = fields.Char('Google Calendar Id', copy=False)
    need_sync = fields.Boolean(default=True, copy=False)
    active = fields.Boolean(default=True)

    def write(self, vals):
        google_service = GoogleCalendarService(self.env['google.service'])
        if 'google_id' in vals:
            self._from_google_ids.clear_cache(self)
        synced_fields = self._get_google_synced_fields()
        if 'need_sync' not in vals and vals.keys() & synced_fields:
            vals['need_sync'] = True

        result = super().write(vals)
        for record in self.filtered('need_sync'):
            if record.google_id:
                record._google_patch(google_service, record.google_id, record._google_values(), timeout=3)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('google_id') for vals in vals_list):
            self._from_google_ids.clear_cache(self)
        records = super().create(vals_list)

        google_service = GoogleCalendarService(self.env['google.service'])
        records_to_sync = records.filtered(lambda r: r.need_sync and r.active)
        for record in records_to_sync:
            record._google_insert(google_service, record._google_values(), timeout=3)
        return records

    def unlink(self):
        """We can't delete an event that is also in Google Calendar. Otherwise we would
        have no clue that the event must must deleted from Google Calendar at the next sync.
        """
        synced = self.filtered('google_id')
        # LUL TODO find a way to get rid of this context key
        if self.env.context.get('archive_on_error') and self._active_name:
            synced.write({self._active_name: False})
            self = self - synced
        elif synced:
            # Since we can not delete such an event (see method comment), we archive it.
            # Notice that archiving an event will delete the associated event on Google.
            # Then, since it has been deleted on Google, the event is also deleted on Odoo DB (_sync_google2odoo).
            self.action_archive()
            return True
        return super().unlink()

    @api.model
    @ormcache_context('google_ids', keys=('active_test',))
    def _from_google_ids(self, google_ids):
        if not google_ids:
            return self.browse()
        return self.search([('google_id', 'in', google_ids)])

    def _sync_odoo2google(self, google_service: GoogleCalendarService):
        if not self:
            return
        if self._active_name:
            records_to_sync = self.filtered(self._active_name)
        else:
            records_to_sync = self
        cancelled_records = self - records_to_sync

        updated_records = records_to_sync.filtered('google_id')
        new_records = records_to_sync - updated_records
        for record in cancelled_records.filtered('google_id'):
            record._google_delete(google_service, record.google_id)
        for record in new_records:
            record._google_insert(google_service, record._google_values())
        for record in updated_records:
            record._google_patch(google_service, record.google_id, record._google_values())

    def _cancel(self):
        self.google_id = False
        self.unlink()

    @api.model
    def _sync_google2odoo(self, google_events: GoogleEvent, default_reminders=()):
        """Synchronize Google recurrences in Odoo. Creates new recurrences, updates
        existing ones.

        :param google_recurrences: Google recurrences to synchronize in Odoo
        :return: synchronized odoo recurrences
        """
        existing = google_events.exists(self.env)
        new = google_events - existing - google_events.cancelled()

        odoo_values = [
            dict(self._odoo_values(e, default_reminders), need_sync=False)
            for e in new
        ]
        new_odoo = self.with_context(dont_notify=True)._create_from_google(new, odoo_values)
        # Synced recurrences attendees will be notified once _apply_recurrence is called.
        if not self._context.get("dont_notify") and all(not e.is_recurrence() for e in google_events):
            new_odoo._notify_attendees()

        cancelled = existing.cancelled()
        cancelled_odoo = self.browse(cancelled.odoo_ids(self.env))
        cancelled_odoo._cancel()
        synced_records = (new_odoo + cancelled_odoo).with_context(dont_notify=self._context.get("dont_notify", False))
        for gevent in existing - cancelled:
            # Last updated wins.
            # This could be dangerous if google server time and odoo server time are different
            updated = parse(gevent.updated)
            odoo_record = self.browse(gevent.odoo_id(self.env))
            # Migration from 13.4 does not fill write_date. Therefore, we force the update from Google.
            if not odoo_record.write_date or updated >= pytz.utc.localize(odoo_record.write_date):
                vals = dict(self._odoo_values(gevent, default_reminders), need_sync=False)
                odoo_record._write_from_google(gevent, vals)
                synced_records |= odoo_record

        return synced_records

    @after_commit
    def _google_delete(self, google_service: GoogleCalendarService, google_id, timeout=TIMEOUT):
        with google_calendar_token(self.env.user.sudo()) as token:
            if token:
                google_service.delete(google_id, token=token, timeout=timeout)
                # When the record has been deleted on our side, we need to delete it on google but we don't want
                # to raise an error because the record don't exists anymore.
                self.exists().need_sync = False

    @after_commit
    def _google_patch(self, google_service: GoogleCalendarService, google_id, values, timeout=TIMEOUT):
        with google_calendar_token(self.env.user.sudo()) as token:
            if token:
                google_service.patch(google_id, values, token=token, timeout=timeout)
                self.need_sync = False

    @after_commit
    def _google_insert(self, google_service: GoogleCalendarService, values, timeout=TIMEOUT):
        if not values:
            return
        with google_calendar_token(self.env.user.sudo()) as token:
            if token:
                send_updates = self._context.get('send_updates', True)
                google_service.google_service = google_service.google_service.with_context(send_updates=send_updates)
                google_id = google_service.insert(values, token=token, timeout=timeout)
                self.write({
                    'google_id': google_id,
                    'need_sync': False,
                })

    def _get_records_to_sync(self, full_sync=False):
        """Return records that should be synced from Odoo to Google

        :param full_sync: If True, all events attended by the user are returned
        :return: events
        """
        domain = self._get_sync_domain()
        if not full_sync:
            is_active_clause = (self._active_name, '=', True) if self._active_name else expression.TRUE_LEAF
            domain = expression.AND([domain, [
                '|',
                    '&', ('google_id', '=', False), is_active_clause,
                    ('need_sync', '=', True),
            ]])
        return self.with_context(active_test=False).search(domain)

    def _write_from_google(self, gevent, vals):
        self.write(vals)

    @api.model
    def _create_from_google(self, gevents, vals_list):
        return self.create(vals_list)

    @api.model
    def _odoo_values(self, google_event: GoogleEvent, default_reminders=()):
        """Implements this method to return a dict of Odoo values corresponding
        to the Google event given as parameter
        :return: dict of Odoo formatted values
        """
        raise NotImplementedError()

    def _google_values(self):
        """Implements this method to return a dict with values formatted
        according to the Google Calendar API
        :return: dict of Google formatted values
        """
        raise NotImplementedError()

    def _get_sync_domain(self):
        """Return a domain used to search records to synchronize.
        e.g. return a domain to synchronize records owned by the current user.
        """
        raise NotImplementedError()

    def _get_google_synced_fields(self):
        """Return a set of field names. Changing one of these fields
        marks the record to be re-synchronized.
        """
        raise NotImplementedError()

    def _notify_attendees(self):
        """ Notify calendar event partners.
        This is called when creating new calendar events in _sync_google2odoo.
        At the initialization of a synced calendar, Odoo requests all events for a specific
        GoogleCalendar. Among those there will probably be lots of events that will never triggers a notification
        (e.g. single events that occured in the past). Processing all these events through the notification procedure
        of calendar.event.create is a possible performance bottleneck. This method aimed at alleviating that.
        """
        raise NotImplementedError()
