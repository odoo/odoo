import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService

_logger = logging.getLogger(__name__)


class HrEmployeeLocation(models.Model):
    _name = 'hr.employee.location'
    _inherit = ['hr.employee.location', 'google.calendar.sync']

    def _get_event_user(self):
        self.ensure_one()
        return self.employee_id.user_id if self.employee_id.user_id.sudo().google_calendar_token else self.env.user

    def _is_google_insertion_blocked(self, sender_user):
        self.ensure_one()
        return self.employee_id.user_id and self.employee_id.user_id != sender_user

    def _is_event_over(self):
        self.ensure_one()
        return self.date < fields.Date.context_today(self)

    def _need_video_call(self):
        self.ensure_one()
        return False

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

    def _get_sync_domain(self):
        return Domain('employee_id.user_id', '=', self.env.user.id)

    def _get_google_synced_fields(self):
        return {'date', 'employee_id', 'work_location_id'}

    def _archive_synced_on_unlink(self):
        return False

    @api.model
    def _restart_google_sync(self):
        self.search(self._get_sync_domain()).write({
            'need_sync': True,
        })

    @api.ondelete(at_uninstall=False)
    def _unlink_delete_synced_google_event(self):
        synced = self.filtered('google_id')
        if synced:
            google_service = GoogleCalendarService(self.env['google.service'])
            for location in synced:
                location.with_user(location._get_event_user())._google_delete(google_service, location.google_id)
