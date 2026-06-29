import logging

from requests import HTTPError
from urllib.parse import quote

from odoo import api, fields, models, Command
from odoo.addons.google_calendar.models.google_sync import google_calendar_token, after_commit
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.fields import Domain


_logger = logging.getLogger(__name__)


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _inherit = ['calendar.calendar', 'google.sync']

    google_sync_token = fields.Char('Sync Token')
    linked_email = fields.Char('Linked Email', readonly=True)

    @staticmethod
    def _get_google_synced_fields_map():
        return {'name': 'summary'}

    def _google_values(self):
        return {google_field: getattr(self, odoo_field) for odoo_field, google_field in
            self._get_google_synced_fields_map().items()}

    def write(self, vals):
        synced_fields = self._get_google_synced_fields_map().keys() | {'active'}
        if 'need_sync' not in vals and vals.keys() & synced_fields and not self.env.user.google_synchronization_stopped:
            vals['need_sync'] = True

        result = super().write(vals)

        # When the module is installed, we archive records instead of deleting them
        # ondelete=cascade does not trigger on archivation -> we need to make sure to delete/archive related records
        if not vals.get('active', True):
            self.env['calendar.event'].search([
                ('calendar_id', 'in', self.ids),
            ]).unlink()
            self.env['calendar.recurrence'].search([
                ('calendar_id', 'in', self.ids),
            ]).unlink()
            self.env['calendar.calendar.user'].search([
                ('calendar_id', 'in', self.ids)
            ]).unlink()

        if self.env.user._get_google_sync_status() == "sync_active":
            google_service = GoogleCalendarService(self.env['google.service'])
            for record in self:
                if record.need_sync and record.google_id and record.active:
                    record._google_calendar_patch(google_service)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        google_service = GoogleCalendarService(self.env['google.service'])
        if self.env.user._get_google_sync_status() == "sync_active":
            for record in records:
                if record.need_sync and record.owner == self.env.user and record.active:
                    record._google_calendar_insert(google_service)
        return records

    def _sync_calendars_google2odoo(self, google_calendars: GoogleCalendar):
        existing = google_calendars.exists(self.env)
        primary = google_calendars.get_primary()
        deleted = google_calendars.get_deleted()
        updated = existing - deleted
        new = google_calendars - updated - primary - deleted

        if primary:
            self.env.user.primary_calendar.write({'google_id': primary.id})

        # Create
        self._create_odoo_calendars(new)
        # Delete
        deleted_odoo = self.browse(deleted.odoo_ids(self.env)).filtered(lambda c: c.owner == self.env.user and not c.is_primary)
        if deleted_odoo:
            deleted_odoo.with_context(dont_notify=True).write({'google_id': False})
            deleted_odoo.unlink()
        # Update
        for calendar in updated:
            odoo_record = self.browse(calendar.odoo_id(self.env))
            # Unlike for events, the calendar endpoints do not return an 'updated' timestamp, meaning we can't
            # rely on last write date to determine which update wins in case of a conflict - we have to decide
            # which side is authoritative. In this case -> Odoo
            if not odoo_record.exists() or odoo_record.need_sync:
                # The record must have been edited or deleted in the meantime
                continue

            odoo_record.sudo().with_context(dont_notify=True).write(dict(odoo_record._odoo_values(calendar), need_sync=False))

    def _sync_calendars_odoo2google(self, calendar_service):
        if not self or self.env.user._get_google_sync_status() != "sync_active":
            return

        # Do not delete the calendars on the side of Google, we do not want to handle such destructive flows
        # Instead, we just archive it on our side so that it is no longer synchronized.
        records_to_sync = self.filtered(self._active_name) if self._active_name else self
        for calendar in records_to_sync:
            if not calendar.google_id and not calendar.is_primary:
                calendar._google_calendar_insert(calendar_service)
            else:
                calendar._google_calendar_patch(calendar_service)

    def _create_odoo_calendars(self, google_calendars: GoogleCalendar):
        if not google_calendars:
            return
        # sudo because we might create shared calendars where the user is only a reader and doesn't have create rights
        self.sudo().create([dict(self._odoo_values(c), need_sync=False) for c in google_calendars])

    def _odoo_values(self, google_record: GoogleCalendar):
        existing_calendar_user = self.calendar_users.filtered(lambda c: c.user_id == self.env.user and c.calendar_id.id == google_record.odoo_id(self.env))
        if existing_calendar_user and google_record.accessRole:
            command = Command.update(existing_calendar_user.id, {
                'access_role': google_record.accessRole,
                'label': google_record.summary,
            })
        else:
            command = Command.create({
                'user_id': self.env.user.id,
                'access_role': google_record.accessRole or 'freeBusyReader',
                'is_filter_active': True,
                'is_filter_checked': True,
                'label': google_record.summary,
            })

        return {
            'calendar_users': [command],
            'google_id': google_record.id,
        }

    @after_commit
    def _google_calendar_patch(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                calendar_service.patch_calendar(self.get_google_path(), self._google_values(), token=token)
                self.exists().with_context(dont_notify=True).need_sync = False
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    @after_commit
    def _google_calendar_delete(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                calendar_service.delete_calendar(self.get_google_path(), token=token)
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    @after_commit
    def _google_calendar_insert(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                response = calendar_service.insert_calendar(self._google_values(), token=token)
                self.with_context(dont_notify=True).write({
                    'google_id': response['id'],
                    'linked_email': self.env.user.google_account_email,
                    'need_sync': False,
                })
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    def _google_error_handling(self, http_error):
        response = http_error.response.json()
        reason = "Google gave the following explanation: %s" % response['error'].get('message')
        if not self.exists():
            _logger.error("Error while syncing calendar. It does not exists anymore in the database. %s", reason)
        else:
            _logger.error("Error while syncing calendar. %s", reason)

    def _get_sync_domain(self):
        return Domain([('user_has_write_access', '=', True)])

    @api.model
    def _restart_google_sync(self):
        calendars = self.env['calendar.calendar'].search(self._get_sync_domain())
        calendars.write({'need_sync': True})
        # When synchronized, we do not delete calendars in Google. Instead of deleting them in Odoo, we archive
        # them so that we know not to sync again. On a reset, we remove them so that they can be synced again.
        deleted = calendars.filtered(lambda c: not c.active)
        deleted.write({'google_id': False})  # unlink instead of archive
        deleted.unlink()

    def get_google_path(self):
        """Return the api path to the calendar in Google, or false if it should not be synchronized."""
        if self.is_primary:
            return 'primary'
        if self.google_id:
            return quote(self.google_id, safe='')
        return False
