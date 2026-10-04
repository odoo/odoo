import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService

_logger = logging.getLogger(__name__)


class HrEmployeeLocation(models.Model):
    _name = 'hr.employee.location'
    _inherit = ['hr.employee.location', 'google.event.sync']

    def _archive_synced_on_unlink(self):
        # Dated exceptions must be removed immediately so another location can
        # be assigned to the same employee and date.
        return False

    def _get_event_owner(self):
        self.ensure_one()
        return self.employee_id.user_id

    def _get_event_user(self):
        self.ensure_one()
        return self.employee_id.user_id

    def _get_sync_domain(self):
        return Domain('employee_id.user_id', '=', self.env.user.id) & Domain('date', '!=', False)

    def _get_records_to_sync(self, calendar, full_sync=False):
        # Working locations belong to the employee's primary calendar and have
        # no calendar_id, unlike meetings and recurrences.
        if calendar != self.env.user.primary_calendar_id or not calendar.google_sync_enabled:
            return self.browse()
        domain = self._get_sync_domain()
        if not full_sync:
            domain &= Domain('google_id', '=', False) | Domain('need_sync', '=', True)
        return self.search(domain, limit=200)

    def _get_google_calendar_path(self):
        return 'primary'

    def _get_google_synced_fields(self):
        return {'date', 'employee_id', 'work_location_id'}

    def _google_values(self):
        self.ensure_one()
        values = {
            'id': self.google_id,
            'eventType': 'workingLocation',
            'start': {'date': self.date.isoformat(), 'dateTime': None},
            'end': {'date': (self.date + relativedelta(days=1)).isoformat(), 'dateTime': None},
            'summary': self.env._('Working location'),
            'organizer': {'email': self.employee_id.user_id.email, 'self': self.employee_id.user_id == self.env.user},
            'visibility': 'public',
            'transparency': 'transparent',
            'extendedProperties': {
                'shared': {
                    '%s_owner_id' % self.env.cr.dbname: str(self.employee_id.user_id.id),
                },
            },
        }
        if self.work_location_type == 'home':
            values['workingLocationProperties'] = {'type': 'homeOffice'}
        elif self.work_location_type == 'office':
            values['workingLocationProperties'] = {
                'type': 'officeLocation',
                'officeLocation': {'label': self.work_location_name},
            }
        else:
            values['workingLocationProperties'] = {
                'type': 'customLocation',
                'customLocation': {'label': self.work_location_name},
            }
        return values

    def _google_error_handling(self, http_error):
        response = http_error.response.json()
        self.exists().with_context(dont_notify=True).need_sync = False
        _logger.error(
            "Error while syncing work location: Google gave the following explanation: %s",
            response['error'].get('message'),
        )

    def _is_event_over(self):
        self.ensure_one()
        return self.date < fields.Date.context_today(self)

    def _need_video_call(self):
        self.ensure_one()
        return False

    @api.model
    def _restart_google_sync(self):
        self.search(self._get_sync_domain()).write({
            'need_sync': True,
        })

    def _should_be_synced(self):
        self.ensure_one()
        owner = self._get_event_owner()
        return bool(self.need_sync and self.date and owner and owner.with_user(owner).primary_calendar_id.google_sync_enabled)

    @api.ondelete(at_uninstall=False)
    def _unlink_delete_synced_google_event(self):
        synced = self.filtered('google_id')
        if synced:
            google_service = GoogleCalendarService(self.env['google.service'])
            for location in synced:
                location.with_user(location._get_event_user())._google_delete(
                    google_service, location._get_google_calendar_path(), location.google_id
                )
