import logging

from requests import HTTPError
from urllib.parse import quote

from odoo import api, fields, models, Command
from odoo.addons.google_calendar.models.google_sync import google_calendar_token, after_commit
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.fields import Domain


_logger = logging.getLogger(__name__)

# The meaning of 'owner' is different in Google and Odoo. See _get_odoo_access_role for more info.
GOOGLE_TO_ODOO_ACCESS_ROLE = {
    "freeBusyReader": "freeBusyReader",
    "reader": "reader",
    "writer": "writer",
    "writerWithoutPrivateAccess": "writer",
    "owner": "writer",
}


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _inherit = ['calendar.calendar', 'google.sync']

    google_sync_token = fields.Char(related='calendar_user_id.google_sync_token')
    google_sync_enabled = fields.Boolean(related='calendar_user_id.google_sync_enabled', readonly=False)
    # When we first create new calendars from Google, we don't want to import them immediately. Calendars with
    # `is_import_pending` set to True should be hidden in the calendar sidebar, and events should not be added to them.
    # The user can choose to import them by enabling the sync for them in the user preferences or the calendar list view.
    # Once the user enables sync, the calendar will be imported and the `is_import_pending` field will be set to False.
    # When we stop sync or uninstall the module, we need to remove all pending calendars.
    is_import_pending = fields.Boolean('Needs Import', readonly=True)

    @staticmethod
    def _get_google_synced_fields_map():
        return {'name': 'summary'}

    def _google_values(self):
        self.ensure_one()
        return {
            google_field: self[odoo_field]
            for odoo_field, google_field in self._get_google_synced_fields_map().items()
        }

    def _google_patch_values(self):
        return {'summaryOverride': self.display_name}

    def write(self, vals):
        synced_fields = self._get_google_synced_fields_map().keys()

        if 'need_sync' not in vals and vals.keys() & synced_fields and not self.env.user.google_synchronization_stopped:
            vals['need_sync'] = True

        result = super().write(vals)

        if self.env.user._get_google_sync_status() == "sync_active":
            for record in self:
                if record.need_sync and record.google_id and record.google_sync_enabled:
                    record._google_calendar_patch(GoogleCalendarService(self.env['google.service']))

        return result

    def unlink(self):
        # Ensure that the calendar syncs back on the next sync so that it can be reimported
        self.env.user.google_calendar_sync_token = False
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.user._get_google_sync_status() == "sync_active":
            for record in records:
                if record.need_sync and self.env.user == record.owner_id and record.google_sync_enabled:
                    record._google_calendar_insert(GoogleCalendarService(self.env['google.service']))
        return records

    @api.model
    def _sync_calendars_google2odoo(self, google_calendars: GoogleCalendar):
        existing = google_calendars.exists(self.env)
        primary = google_calendars.get_primary()
        deleted = google_calendars.get_deleted()
        updated = existing - deleted
        new = google_calendars - updated - primary - deleted

        if primary:
            self.env.user._find_or_create_primary_calendar().write({'google_id': primary.id})

        # Create
        if new:
            # sudo is needed because we might create shared calendars where the user is only a reader and doesn't have create rights
            self.sudo().create([dict(
                self._odoo_values(google_calendar, self.env['calendar.calendar']),
                need_sync=False
            ) for google_calendar in new])

        # Delete
        deleted_odoo = self.browse(deleted.odoo_ids(self.env)).filtered(lambda c: not c.is_primary)
        if deleted_odoo and deleted_odoo.calendar_user_id:
            # Deleting the last calendar user also deletes the calendar, so we don't need to unlink it directly
            deleted_odoo.calendar_user_id.unlink()
        # Update
        for calendar in updated:
            odoo_record = self.browse(calendar.odoo_id(self.env))
            # Unlike for events, the calendar endpoints do not return an 'updated' timestamp, meaning we can't
            # rely on last write date to determine which update wins in case of a conflict - we have to decide
            # which side is authoritative. In this case -> Odoo
            if odoo_record.need_sync:
                # The record must have been edited or deleted in the meantime
                continue

            # This update may cause a change in the access role (e.g., grant the user higher privilege) -> sudo is needed
            odoo_record.sudo().with_context(dont_notify=True).write(dict(self.env['calendar.calendar']._odoo_values(calendar, odoo_record), need_sync=False))

        return bool(new)

    def _sync_calendars_odoo2google(self, calendar_service):
        if not self or self.env.user._get_google_sync_status() != "sync_active":
            return

        # Unlike for event sync, we only insert and update calendars. We never delete calendars
        # on the side of Google - we do not want to handle such destructive flows
        for calendar in self:
            if not calendar.google_id and not calendar.is_primary:
                if self.env.user == calendar.owner_id:
                    calendar._google_calendar_insert(calendar_service)
            else:
                calendar._google_calendar_patch(calendar_service)

    @api.model
    def _odoo_values(self, google_record: GoogleCalendar, odoo_calendar):
        new_access_role = self._get_odoo_access_role(google_record)
        # Multiple odoo users can sync with the same Google account, which could lead to multiple calendar owners.
        # We want to restrict calendars to have a single owner, so in this edge case, we demote the second one to a writer.
        if new_access_role == 'owner' and odoo_calendar.calendar_user_ids.filtered(
                lambda c: c.access_role == 'owner' and c.user_id != self.env.user):
            new_access_role = 'writer'

        existing_calendar_user = odoo_calendar.calendar_user_id
        if existing_calendar_user:
            command = Command.update(existing_calendar_user.id, {
                'access_role': new_access_role or existing_calendar_user.access_role,
                'name': google_record.summaryOverride or google_record.summary or existing_calendar_user.name,
            })
        else:
            command = Command.create({
                'user_id': self.env.user.id,
                'access_role': new_access_role or 'freeBusyReader',
                'google_sync_enabled': False,  # Do not sync calendars by default, the user has to enable it manually
                'is_filter_active': False,
                'is_filter_checked': False,
                'name': google_record.summaryOverride or google_record.summary,
            })

        return {
            'name': google_record.summary,
            'calendar_user_ids': [command],
            'google_id': google_record.id,
            'calendar_default_privacy': 'members_only',
            'is_import_pending': not odoo_calendar or odoo_calendar.is_import_pending,  # Hide the calendar until the user chooses to sync it
        }

    @api.model
    def _get_odoo_access_role(self, google_record: GoogleCalendar):
        """Map a Google Calendar ACL access role to the corresponding Odoo access role.

        In Google, anyone with the access level of 'Make changes and manage sharing' is an owner
        Google docs: "The owner role is different from the calendar's data owner.
        A calendar has a single data owner, but can have multiple users with owner role."
        https://developers.google.com/workspace/calendar/api/v3/reference/acl

        The data owner is only set for secondary calendars, a shared primary calendar record does
        not specify a data owner. Instead, the primary flag is used - it's only present if
        it is the current user's primary calendar
        """
        if (google_record.primary or (google_record.accessRole == 'owner'
                and google_record.dataOwner
                and google_record.dataOwner == self.env.user.google_account_email)):
            return 'owner'
        else:
            return GOOGLE_TO_ODOO_ACCESS_ROLE.get(google_record.accessRole, False)

    @after_commit
    def _google_calendar_patch(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                if self.user_access_role == 'owner':
                    # Rename the calendar object directly
                    calendar_service.patch_calendar(self.get_google_path(), self._google_values(), token=token)
                else:
                    # To update the label override for a calendar we do not own, we use the calendarList endpoint
                    # which does not support the /primary path -> we always use the calendar id in the path.
                    calendar_service.patch_calendar_list_entry(quote(self.google_id, safe=''), self._google_patch_values(), token=token)
                self.exists().with_context(dont_notify=True).need_sync = False
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    @after_commit
    def _google_calendar_insert(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                response = calendar_service.insert_calendar(self._google_values(), token=token)
                self.with_context(dont_notify=True).write({
                    'google_id': response['id'],
                    'need_sync': False,
                })
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    def _google_error_handling(self, http_error):
        response = http_error.response.json()
        reason = f"Google gave the following explanation: {response['error'].get('message')}"
        if not self.exists():
            _logger.error("Error while syncing calendar. It does not exists anymore in the database. %s", reason)
        else:
            _logger.error("Error while syncing calendar. %s", reason)

    def _get_sync_domain(self):
        return Domain([('calendar_user_ids', 'any', [('user_id', '=', self.env.user.id), ('access_role', 'in', ['owner', 'writer'])])])

    @api.model
    def _restart_google_sync(self):
        calendars = self.env['calendar.calendar'].search(self._get_sync_domain())
        calendars.write({'need_sync': True})

    def get_google_path(self):
        """Return the api path to the calendar in Google, or false if it should not be synchronized."""
        if self.is_primary:
            return 'primary'
        if self.google_id:
            return quote(self.google_id, safe='')
        return False

    def _get_public_writable_fields(self):
        """ When calendars are created from Google, they have the 'is_import_pending' flag set to True.
        Any user with a calendar user record on the calendar should be able to enable sync for it,
        regardless of the access role. Otherwise, read-only calendars could never be imported."""
        return super()._get_public_writable_fields() | {'google_sync_enabled', 'is_import_pending'}
