# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tools import frozendict
from odoo.tests.common import new_test_user
from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleEvent
from unittest.mock import patch


@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncWorkLocationsGoogle(TestSyncGoogle):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_location_user = new_test_user(cls.env, login='work_location-user')

        cls.hr_employee = cls.env['hr.employee'].create({
            'name': 'Employee for HR Work Location Test',
            'user_id': cls.work_location_user.id,
            'work_contact_id': cls.work_location_user.partner_id.id,
        })

        cls.work_location_simple_values = frozendict({
            "eventType": "workingLocation",
            'description': 'Working location',
            'summary': 'Working location',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'transparency': 'transparent',
            'extendedProperties': {
                'shared':  {'%s_owner_id' % cls.env.cr.dbname: str(cls.work_location_user.id)}
            },
        })

    @patch_api
    def test_work_locations_google_allday_to_odoo_hr(self):
        with self.mock_datetime_and_now("2025-04-28"):
            office_location_values = {
                **self.work_location_simple_values,
                'id': 'workingLocation_office',
                'start': {'date': '2025-04-28', 'dateTime': None},
                'end': {'date': '2025-04-29', 'dateTime': None},
                'workingLocationProperties': {
                    'type': 'officeLocation',
                    'officeLocation': {
                        'label': 'Odoo Farm 1: R&D Vidange Office'
                    }
                }
            }

            home_location_values = {
                **self.work_location_simple_values,
                'id': 'workingLocation_home',
                'start': {'date': '2025-04-29', 'dateTime': None},
                'end': {'date': '2025-04-30', 'dateTime': None},
                'workingLocationProperties': {
                    'type': 'homeOffice',
                    'homeOffice': {
                        'label': 'Home'
                    }
                }
            }

            custom_location_values = {
                **self.work_location_simple_values,
                'id': 'workingLocation_custom',
                'start': {'date': '2025-04-30', 'dateTime': None},
                'end': {'date': '2025-05-01', 'dateTime': None},
                'workingLocationProperties': {
                    'type': 'customLocation',
                    'customLocation': {
                        'label': 'Odoo Louvain-la-Neuve Office'
                    }
                }
            }

            custom_location_same_values = {
                **self.work_location_simple_values,
                'id': 'workingLocation_custom_same',
                'start': {'date': '2025-05-01', 'dateTime': None},
                'end': {'date': '2025-05-02', 'dateTime': None},
                'workingLocationProperties': {
                    'type': 'customLocation',
                    'customLocation': {
                        'label': 'Odoo Louvain-la-Neuve Office'
                    }
                }
            }

            previous_work_locations_count = self.env['hr.work.location'].search_count([])

            self.env['calendar.event'].with_user(self.work_location_user)._sync_google2odoo(
                GoogleEvent([office_location_values, home_location_values, custom_location_values, custom_location_same_values])
            )

            current_work_locations_count = self.env['hr.work.location'].search_count([])
            self.assertEqual(
                current_work_locations_count,
                previous_work_locations_count + 2,
            )
            office_location = self.env['hr.work.location'].search([('name', '=', 'Odoo Farm 1: R&D Vidange Office')])
            home_location = self.env['hr.work.location'].search([('name', '=', 'Home')])
            custom_location = self.env['hr.work.location'].search([('name', '=', 'Odoo Louvain-la-Neuve Office')])

            employee_locations = self.env['hr.employee.location'].search([
                ('employee_id', '=', self.hr_employee.id),
                ('date', '>=', '2025-04-28'),
                ('date', '<=', '2025-05-01'),
            ], order='date')
            self.assertRecordValues(employee_locations, [
                {'date': date(2025, 4, 28), 'work_location_id': office_location.id, 'google_id': 'workingLocation_office'},
                {'date': date(2025, 4, 29), 'work_location_id': home_location.id, 'google_id': 'workingLocation_home'},
                {'date': date(2025, 4, 30), 'work_location_id': custom_location.id, 'google_id': 'workingLocation_custom'},
                {'date': date(2025, 5, 1), 'work_location_id': custom_location.id, 'google_id': 'workingLocation_custom_same'},
            ])

    @patch_api
    def test_work_location_odoo_to_google(self):
        home_location = self.env.ref('hr.home_work_location')
        employee_location = self.env['hr.employee.location'].with_user(self.work_location_user).create({
            'employee_id': self.hr_employee.id,
            'date': '2025-04-29',
            'work_location_id': home_location.id,
            'need_sync': False,
        })

        employee_location._sync_odoo2google(self.google_service)
        self.assertGoogleEventInserted({
            'id': False,
            'eventType': 'workingLocation',
            'start': {'date': '2025-04-29', 'dateTime': None},
            'end': {'date': '2025-04-30', 'dateTime': None},
            'workingLocationProperties': {'type': 'homeOffice'},
        })

        employee_location.google_id = 'workingLocation_home'
        employee_location.unlink()
        self.assertFalse(employee_location.exists())
        self.assertGoogleEventDeleted('workingLocation_home')
