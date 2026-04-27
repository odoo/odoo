from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch


from odoo.addons.appointment_google_reserve.tests.common import GoogleReserveCommon
from odoo.tests import tagged


@tagged('appointment_google_reserve')
class AppointmentGoogleReserveAPITest(GoogleReserveCommon):

    @freeze_time('2022-02-14 07-00-00')
    def test_appointment_resource_sync(self):
        # initial assertion
        self.assertFalse(self.apt_type_resource_google.google_reserve_pending_sync)

        # 1. write on unrelated field: nothing happens
        self.apt_resources_google.write({'name': 'Updated Name'})
        self.assertFalse(self.apt_type_resource_google.google_reserve_pending_sync)

        # 2. write on capacity: update related appointment availabilities
        self.apt_resources_google.write({'capacity': 3})
        self.assertTrue(self.apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        self.apt_type_resource_google.google_reserve_pending_sync = False

        # 3. archive -> update related appointment availabilities
        self.apt_resources_google.toggle_active()
        self.assertTrue(self.apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        self.apt_type_resource_google.google_reserve_pending_sync = False

        # 4. restore -> update related appointment availabilities (again)
        self.apt_resources_google.toggle_active()
        self.assertTrue(self.apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        self.apt_type_resource_google.google_reserve_pending_sync = False

        # 4. restore -> update related appointment availabilities (again)
        self.apt_resources_google.unlink()
        self.assertTrue(self.apt_type_resource_google.google_reserve_pending_sync)

    @freeze_time('2022-02-14 07-00-00')
    @patch('odoo.addons.appointment_google_reserve.tools.google_reserve_iap.iap_jsonrpc')
    def test_appointment_type_sync(self, iap_jsonrpc):
        """ When an appointment is created, we need to check that it's registered on IAP.
        When an appointment is modified, we need to check that:
          - It's updated on IAP
          - It's marked as requiring sync

        The following use cases are taken into account:
        - Creation of an appointment.type
        - Modification of an appointment.type
          - Only for relevant fields
          - Some fields need to re-register the appointment on IAP
          - Some fields need to update the availabilities on IAP
          - (Some need to do both)
        - Archive/Restore an appointment.type
        - Unlink an appointment.type """

        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        self.env['ir.config_parameter'].sudo().set_param(
            'appointment_google_reserve.google_reserve_iap_endpoint',
            'https://google-reserve.api.odoo.com'
        )

        # 1. create an appointment.type: needs to be registered on IAP
        apt_type_resource_google = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'assign_method': 'time_auto_assign',
            'location_id': self.test_location.id,
            'min_schedule_hours': 1.0,
            'max_schedule_days': 5,
            'name': 'Test Google Reserve',
            'resource_manage_capacity': True,
            'schedule_based_on': 'resources',
            'google_reserve_enable': True,
            'google_reserve_merchant_id': self.google_reserve_merchant.id,
            'slot_ids': [(0, 0, {
                'weekday': str(self.reference_monday.isoweekday()),
                'start_hour': 15,
                'end_hour': 18,
            })],
        })
        access_token = apt_type_resource_google.google_reserve_access_token

        # assert initial data
        self.assertFalse(apt_type_resource_google.google_reserve_pending_sync)

        self.env['appointment.resource'].create([{
            'appointment_type_ids': apt_type_resource_google.ids,
            'capacity': 2,
            'name': 'Table 1',
            'sequence': 2,
        }, {
            'appointment_type_ids': apt_type_resource_google.ids,
            'capacity': 4,
            'name': 'Table 2',
            'sequence': 1,
        }])

        appointment_data = {
            'db_uuid': db_uuid,
            'merchant_details': {
                'name': 'My Company',
                'id': self.google_reserve_merchant.id,
                'callback_url': apt_type_resource_google.get_base_url(),
                'business_category': 'Restaurant',
                'phone': '+32499123456',
                'website_url': 'https://www.example.com',
                'location': {
                    'country_code': 'BE',
                    'city': 'Bloups',
                    'region': False,
                    'zip': '6666',
                    'street': 'Zboing Street 42',
                }
            },
            'appointment_details': {
                'appointment_type_id': apt_type_resource_google.id,
                'google_reserve_access_token': apt_type_resource_google.google_reserve_access_token,
                'service_name': 'Test Google Reserve',
                'min_cancellation_hours': 1.0,
                'min_schedule_hours': 1.0
            }
        }

        self.assertEqual(iap_jsonrpc.call_count, 1)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[0],
            'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/register',
            appointment_data,
        )

        # 2a. writing on an unrelated field, should not call IAP
        apt_type_resource_google.write({'sequence': 42})
        self.assertEqual(iap_jsonrpc.call_count, 1)
        self.assertFalse(apt_type_resource_google.google_reserve_pending_sync)

        # 2b. writing on a field that alters both the slots and the appointment definition on IAP
        # -> call register and mark as needing sync
        apt_type_resource_google.write({'min_cancellation_hours': 2})
        appointment_data['appointment_details']['min_cancellation_hours'] = 2

        self.assertEqual(iap_jsonrpc.call_count, 2)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[1],
            'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/register',
            appointment_data,
        )
        self.assertTrue(apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        apt_type_resource_google.google_reserve_pending_sync = False

        # 2c. writing on a field that alters only the appointment definition
        # -> call appointment registration route for update
        apt_type_resource_google.write({'name': 'Test Google Reserve Edited'})
        self.assertTrue(apt_type_resource_google.google_reserve_pending_sync)

        self.assertEqual(iap_jsonrpc.call_count, 3)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[2],
            'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/register',
            False,  # already tested before
        )

        # reset sync
        apt_type_resource_google.google_reserve_pending_sync = False

        # 2d. writing on a field that alters only the appointment availabilities
        # -> call appointment availabilities replace route
        apt_type_resource_google.write({'appointment_duration': 2})
        self.assertTrue(apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        apt_type_resource_google.google_reserve_pending_sync = False

        # 3. archive -> unregister the appointment from IAP
        apt_type_resource_google.toggle_active()
        self.assertEqual(iap_jsonrpc.call_count, 4)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[3],
            f'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/{access_token}/unregister',
            False,  # nothing relevant to test
        )
        self.assertTrue(apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        apt_type_resource_google.google_reserve_pending_sync = False

        # 4. restore -> register the appointment on IAP again
        apt_type_resource_google.toggle_active()
        self.assertEqual(iap_jsonrpc.call_count, 5)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[4],
            'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/register',
            False,  # already tested before
        )
        self.assertTrue(apt_type_resource_google.google_reserve_pending_sync)

        # reset sync
        apt_type_resource_google.google_reserve_pending_sync = False

        # 5. unlink -> unregister the appointment from IAP
        apt_type_resource_google.unlink()
        self.assertEqual(iap_jsonrpc.call_count, 6)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[5],
            f'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/{access_token}/unregister',
            False,  # already tested before
        )

    @freeze_time('2022-02-14 07-00-00')
    @patch('odoo.addons.appointment_google_reserve.tools.google_reserve_iap.iap_jsonrpc')
    def test_booking_update(self, iap_jsonrpc):
        """ When a calendar.event was created from a Google Reserve booking, we need to notify Google
        every time that booking is updated (or cancelled)

        The following use cases are taken into account:
        - Update of a unrelated calendar.event
        - Update of a Google Reserve calendar.event
          - Date change
          - Party size change
          - Unrelated field change
        - Archive a Google Reserve calendar.event
        - Unlink a Google Reserve calendar.event """

        update_availabilities_url = f'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/{self.apt_type_resource_google.google_reserve_access_token}/update_availabilities'
        update_booking_url = f'https://google-reserve.api.odoo.com/api/google_reserve/1/appointment/{self.apt_type_resource_google.google_reserve_access_token}/update_booking'

        calendar_event = self.env['calendar.event'].create({
            'appointment_type_id': self.apt_type_resource_google.id,
            'name': "New Meeting 1",
            'resource_total_capacity_reserved': 4,
            'start': datetime(2022, 2, 14, 10, 0, 0),
            'stop': datetime(2022, 2, 14, 14, 0, 0),
        })

        calendar_event.write({
            'stop': datetime(2022, 2, 14, 15, 0, 0)
        })

        # 1. not a Google Reserve event: no need to update Google
        # we however did 2 calls to "update_availabilities"
        self.assertEqual(iap_jsonrpc.call_count, 2)
        for i in range(2):
            self.assertIapRpc(
                iap_jsonrpc.call_args_list[i],
                update_availabilities_url,
            )

        # 2. write on dates -> update Google to reflect calendar event changes
        calendar_event.write({
            'is_google_reserve': True,
            'stop': datetime(2022, 2, 14, 14, 0, 0),
        })
        self.assertEqual(iap_jsonrpc.call_count, 4)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[2],
            update_availabilities_url,
        )
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[3],
            update_booking_url,
            {
                'booking_ids': calendar_event.ids,
                'booking_values': {
                    'startTime': '2022-02-14T10:00:00Z',
                    'duration': str(4 * 3600) + 's'  # 4 hours
                },
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            }
        )

        # 3. book for more people -> update Google to reflect calendar event changes
        calendar_event.write({
            'resource_total_capacity_reserved': 6,
        })
        self.assertEqual(iap_jsonrpc.call_count, 6)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[4],
            update_availabilities_url,
        )
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[5],
            update_booking_url,
            {
                'booking_ids': calendar_event.ids,
                'booking_values': {
                    'partySize': '6',
                },
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            }
        )

        # 4. name change -> nothing happens
        calendar_event.write({
            'name': 'Booking for Paul',
        })
        self.assertEqual(iap_jsonrpc.call_count, 6)

        # 5. archive event -> cancel on Google
        calendar_event.write({
            'active': False,
        })
        self.assertEqual(iap_jsonrpc.call_count, 8)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[6],
            update_availabilities_url,
        )
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[7],
            update_booking_url,
            {
                'booking_ids': calendar_event.ids,
                'booking_values': {
                    'status': 'CANCELED',
                },
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            }
        )

        # 6. unlink event -> cancel on Google
        [regular_event, google_event] = self.env['calendar.event'].create([{
            'appointment_type_id': self.apt_type_resource_google.id,
            'name': "New Meeting 2",
            'resource_total_capacity_reserved': 4,
            'start': datetime(2022, 2, 15, 10, 0, 0),
            'stop': datetime(2022, 2, 15, 14, 0, 0),
        }, {
            'appointment_type_id': self.apt_type_resource_google.id,
            'name': "New Meeting 3",
            'resource_total_capacity_reserved': 4,
            'start': datetime(2022, 2, 16, 10, 0, 0),
            'stop': datetime(2022, 2, 16, 14, 0, 0),
            'is_google_reserve': True,
        }])
        self.assertEqual(iap_jsonrpc.call_count, 9)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[8],
            update_availabilities_url,
        )

        (regular_event + google_event).unlink()
        self.assertEqual(iap_jsonrpc.call_count, 11)
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[9],
            update_availabilities_url,
        )
        self.assertIapRpc(
            iap_jsonrpc.call_args_list[10],
            update_booking_url,
            {
                'booking_ids': google_event.ids,
                'booking_values': {
                    'status': 'CANCELED',
                },
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            }
        )

    @freeze_time('2022-02-14 07-00-00')
    @patch('odoo.addons.appointment_google_reserve.tools.google_reserve_iap.GoogleReserveIAP.update_availabilities', autospec=True)
    def test_calendar_event_sync(self, update_availabilities):
        """ When a calendar.event is created or modified, we need to sync the availabilities of the
        underlying appointments that are google reserve enabled.

        The following use cases are taken into account:
        - Creation of a calendar.event
        - Modification of a calendar.event (for relevant fields)
        - Archive/Restore a calendar.event
        - Unlink a calendar.event """

        # 1. create bookings: update related appointment availabilities
        events = self.env['calendar.event'].create([{
            'appointment_type_id': self.apt_type_resource_google.id,
            'name': "New Meeting 1",
            'start': datetime(2022, 2, 14, 10, 0, 0),
            'stop': datetime(2022, 2, 14, 15, 0, 0),
        }, {
            'appointment_type_id': self.apt_type_resource_google.id,
            'name': "New Meeting 2",
            'start': datetime(2022, 2, 14, 17, 0, 0),
            'stop': datetime(2022, 2, 14, 19, 0, 0),
        }])

        self.assertEqual(update_availabilities.call_count, 1)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[0],
            self.apt_type_resource_google,
            datetime(2022, 2, 14, 10, 0, 0),
            datetime(2022, 2, 14, 19, 0, 0)
        )

        # 2. rename bookings: do nothing, it doesn't affect availabilities
        events.write({'name': "Renamed Meeting"})
        self.assertEqual(update_availabilities.call_count, 1)

        # 3. move bookings: update related appointment availabilities
        # -> take min (old start, new start) and max (old stop, new stop)
        events.write({
            'start': datetime(2022, 2, 14, 11, 0, 0),
            'stop': datetime(2022, 2, 14, 20, 0, 0)
        })
        self.assertEqual(update_availabilities.call_count, 2)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[1],
            self.apt_type_resource_google,
            datetime(2022, 2, 14, 10, 0, 0),
            datetime(2022, 2, 14, 20, 0, 0)
        )

        # 4. archive bookings: update related appointment availabilities
        events.toggle_active()
        self.assertEqual(update_availabilities.call_count, 3)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[2],
            self.apt_type_resource_google,
            datetime(2022, 2, 14, 11, 0, 0),
            datetime(2022, 2, 14, 20, 0, 0)
        )

        # 5. restore bookings: update related appointment availabilities
        events.toggle_active()
        self.assertEqual(update_availabilities.call_count, 4)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[3],
            self.apt_type_resource_google,
            datetime(2022, 2, 14, 11, 0, 0),
            datetime(2022, 2, 14, 20, 0, 0)
        )

        # 6. delete bookings: update related appointment availabilities
        events.unlink()
        self.assertEqual(update_availabilities.call_count, 5)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[4],
            self.apt_type_resource_google,
            datetime(2022, 2, 14, 11, 0, 0),
            datetime(2022, 2, 14, 20, 0, 0)
        )
        self.assertFalse(events.exists())

    @freeze_time('2022-02-14 07-00-00')
    @patch('odoo.addons.appointment_google_reserve.tools.google_reserve_iap.GoogleReserveIAP.update_availabilities', autospec=True)
    def test_resource_calendar_leaves_sync(self, update_availabilities):
        """ When a resource.calendar.leaves is created or modified, we need to sync the
        availabilities of the underlying appointment resources' appointments that are google reserve enabled.

        The following use cases are taken into account:
        - Creation of a calendar.resource.leaves
        - Modification of a calendar.resource.leaves (for relevant fields)
        - Unlink a calendar.resource.leaves """

        # 1. create leaves: update related appointment availabilities
        calendar_leaves = self.env['resource.calendar.leaves'].create([{
            'resource_id': appointment_resource.resource_id.id,
            'date_from': datetime(2022, 2, 17, 8, 0, 0),
            'date_to': datetime(2022, 2, 17, 17, 0, 0),
        } for appointment_resource in self.apt_resources_google])

        self.assertEqual(update_availabilities.call_count, 1)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[0],
            self.apt_type_resource_google,
            datetime(2022, 2, 17, 8, 0, 0),
            datetime(2022, 2, 17, 17, 0, 0)
        )

        # 2. change reason: do nothing, it doesn't affect availabilities
        calendar_leaves.write({'name': "New Reason"})
        self.assertEqual(update_availabilities.call_count, 1)

        # 3. move leaves: update related appointment availabilities
        # -> take min (old start, new start) and max (old stop, new stop)
        calendar_leaves.write({
            'date_from': datetime(2022, 2, 17, 11, 0, 0),
            'date_to': datetime(2022, 2, 17, 20, 0, 0)
        })
        self.assertEqual(update_availabilities.call_count, 2)
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[1],
            self.apt_type_resource_google,
            datetime(2022, 2, 17, 8, 0, 0),
            datetime(2022, 2, 17, 20, 0, 0)
        )

        # 4. unlink: update related appointment availabilities
        calendar_leaves.unlink()
        self.assertUpdateAvailabilities(
            update_availabilities.call_args_list[2],
            self.apt_type_resource_google,
            datetime(2022, 2, 17, 11, 0, 0),
            datetime(2022, 2, 17, 20, 0, 0)
        )

    # ------------------------------------------------------------
    # UTILS
    # ------------------------------------------------------------

    def assertIapRpc(self, post_mock_call_args, post_url, post_data=False):
        args, kwargs = post_mock_call_args
        self.assertEqual(args[0], post_url)
        if post_data:
            self.assertDictEqual(kwargs.get('params'), post_data)

    def assertUpdateAvailabilities(self, update_availabilities_call_args, appointment, start=None, stop=None):
        args, _kwargs = update_availabilities_call_args
        self.assertEqual(args[1], appointment)
        if start is not None:
            self.assertEqual(args[2], start)
        if stop is not None:
            self.assertEqual(args[3], stop)
