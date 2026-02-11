# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import new_test_user
from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleEvent
from unittest.mock import patch


@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
class TestSyncWorkLocationsGoogle(TestSyncGoogle):

    def setUp(self):
        super().setUp()
        self.work_location_user = new_test_user(self.env, login='work_location-user')

        self.hr_employee = self.env['hr.employee'].create({
            'name': 'Employee for HR Work Location Test',
            'user_id': self.work_location_user.id,
            'work_contact_id': self.work_location_user.partner_id.id,
        })

        self.work_location_simple_values = {
            "eventType": "workingLocation",
            'id': 'workingLocation',
            'description': 'Working location - MONDAY',
            'summary': 'Working location - MONDAY',
            'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
            'visibility': 'public',
            'attendees': [],
            'reminders': {'useDefault': True},
            'transparency': 'transparent',
            'start': {'date': '2025-04-28', 'dateTime': None},
            'end': {'date': '2025-04-29', 'dateTime': None},
            # Recurrence removed from test data as singleEvents=True returns flattened instances
            'extendedProperties': {
                'shared':  {'%s_owner_id' % self.env.cr.dbname: str(self.work_location_user.id)}
            },
        }

    @patch_api
    def test_office_work_location_google_allday_to_odoo_hr(self):
        with self.mock_datetime_and_now("2025-04-28"):
            office_location_values = self.work_location_simple_values.copy()
            office_location_values['workingLocationProperties'] = {
                'type': 'officeLocation',
                'officeLocation': {
                    'label': 'Odoo Farm 1: R&D Vidange Office'
                }
            }

            self.env['calendar.event'].with_user(self.work_location_user)._sync_google2odoo(
                GoogleEvent([office_location_values])
            )
            event = self.env['calendar.event'].search([('google_id', '=', 'workingLocation')])
            self.assertFalse(event, "The event should not be created in Odoo.")
            self.assertGoogleAPINotCalled()

            hr_location = self.env['hr.work.location'].search([('name', '=', 'Odoo Farm 1: R&D Vidange Office')])
            self.assertTrue(hr_location, "The office location should be created in Odoo.")
            self.assertEqual(self.hr_employee.monday_location_id, hr_location, "Synced location should match.")

    @patch_api
    def test_home_work_location_google_allday_to_odoo_hr(self):
        with self.mock_datetime_and_now("2025-04-28"):
            home_location_values = self.work_location_simple_values.copy()
            home_location_values.update({
                'workingLocationProperties': {
                    'type': 'homeOffice',
                    'homeOffice': {
                        'label': 'Home'
                    }
                }
            })

            previous_work_locations = self.env['hr.work.location'].search([])
            self.env['calendar.event'].with_user(self.work_location_user)._sync_google2odoo(
                GoogleEvent([home_location_values])
            )
            event = self.env['calendar.event'].search([('google_id', '=', 'workingLocation')])
            self.assertFalse(event, "The event should not be created in Odoo.")
            self.assertGoogleAPINotCalled()

            current_work_locations = self.env['hr.work.location'].search([])
            self.assertEqual(
                len(current_work_locations),
                len(previous_work_locations),
                "No new working locations should be created as 'Home' is already pre-defined."
            )
            hr_location = self.env['hr.work.location'].search([('name', '=', 'Home')])
            self.assertEqual(self.hr_employee.monday_location_id, hr_location, "Synced location should match.")

    @patch_api
    def test_custom_location_work_location_google_allday_to_odoo_hr(self):
        with self.mock_datetime_and_now("2025-04-28"):
            custom_location_values = self.work_location_simple_values.copy()
            custom_location_values.update({
                'workingLocationProperties': {
                    'type': 'customLocation',
                    'customLocation': {
                        'label': 'Odoo Louvain-la-Neuve Office'
                    }
                }
            })

            self.env['calendar.event'].with_user(self.work_location_user)._sync_google2odoo(
                GoogleEvent([custom_location_values])
            )
            event = self.env['calendar.event'].search([('google_id', '=', 'workingLocation')])
            self.assertFalse(event, "The event should not be created in Odoo.")
            self.assertGoogleAPINotCalled()

            hr_location = self.env['hr.work.location'].search([('name', '=', 'Odoo Louvain-la-Neuve Office')])
            self.assertTrue(hr_location, "The custom location should be created in Odoo.")
            self.assertEqual(self.hr_employee.monday_location_id, hr_location, "Synced location should match.")
