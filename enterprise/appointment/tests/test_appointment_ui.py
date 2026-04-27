# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz

from datetime import datetime, timedelta
from freezegun import freeze_time
from lxml import html

from odoo import Command, http
from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common, tagged, users


class AppointmentUICommon(AppointmentCommon, common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super(AppointmentUICommon, cls).setUpClass()

        cls.env.user.tz = "Europe/Brussels"
        cls.std_user = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='std_user@test.example.com',
            groups='base.group_user',
            name='Solène StandardUser',
            notification_type='email',
            login='std_user',
            tz='Europe/Brussels'  # UTC + 1 (at least in February)
        )
        cls.portal_user = cls._create_portal_user()

@tagged('appointment_ui', '-at_install', 'post_install')
class AppointmentUITest(AppointmentUICommon):

    @users('apt_manager')
    def test_route_apt_type_search_create_anytime(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        request = self.url_open(
            "/appointment/appointment_type/search_create_anytime",
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', {})
        self.assertTrue(result.get('appointment_type_id'), 'The request returns the id of the custom appointment type')
        appointment_type = self.env['appointment.type'].browse(result['appointment_type_id'])
        self.assertEqual(appointment_type.category, 'anytime')
        self.assertEqual(len(appointment_type.slot_ids), 7, "7 slots have been created: (1 / days for 7 days)")
        self.assertTrue(all(slot.slot_type == 'recurring' for slot in appointment_type.slot_ids), "All slots are 'recurring'")

    @users('apt_manager')
    def test_route_apt_type_search_create_anytime_with_context(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        request = self.url_open(
            "/appointment/appointment_type/search_create_anytime",
            data=json.dumps({
                'params': {
                    'context': {
                        'default_assign_method': 'time_resource',
                    },
                }
            }),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', dict())
        self.assertTrue(result.get('appointment_type_id'), 'The request returns the id of the custom appointment type')

        appointment_type = self.env['appointment.type'].browse(result['appointment_type_id'])
        # All default context fields should be ignored because of clean_context()
        self.assertEqual(appointment_type.assign_method, 'resource_time')

    @users('apt_manager')
    def test_route_apt_type_create_custom(self):
        self.authenticate(self.env.user.login, self.env.user.login)

        with freeze_time(self.reference_now):
            unique_slots = [{
                'start': (datetime.now() + timedelta(hours=1)).replace(microsecond=0).isoformat(' '),
                'end': (datetime.now() + timedelta(hours=2)).replace(microsecond=0).isoformat(' '),
                'allday': False,
            }, {
                'start': (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat(' '),
                'end': (datetime.now() + timedelta(days=3)).replace(microsecond=0).isoformat(' '),
                'allday': True,
            }]
            request = self.url_open(
                "/appointment/appointment_type/create_custom",
                data=json.dumps({
                    'params': {
                        'slots': unique_slots,
                    }
                }),
                headers={"Content-Type": "application/json"},
            ).json()
        result = request.get('result', {})
        self.assertTrue(result.get('appointment_type_id'), 'The request returns the id of the custom appointment type')
        appointment_type = self.env['appointment.type'].browse(result['appointment_type_id'])
        self.assertEqual(appointment_type.category, 'custom')
        self.assertEqual(appointment_type.name, "%s - My availabilities" % self.env.user.name)
        self.assertEqual(len(appointment_type.slot_ids), 2, "Two slots have been created")

        with freeze_time(self.reference_now):
            for slot in appointment_type.slot_ids:
                self.assertEqual(slot.slot_type, 'unique', 'All slots should be unique')
                if slot.allday:
                    self.assertEqual(slot.start_datetime, datetime.now() + timedelta(days=2))
                    self.assertEqual(slot.end_datetime, datetime.now() + timedelta(days=3))
                else:
                    self.assertEqual(slot.start_datetime, datetime.now() + timedelta(hours=1))
                    self.assertEqual(slot.end_datetime, datetime.now() + timedelta(hours=2))

    @users('apt_manager')
    def test_route_create_custom_with_context(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        now = datetime.now()
        unique_slots = [{
            'start': (now + timedelta(hours=1)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(hours=2)).replace(microsecond=0).isoformat(' '),
            'allday': False,
        }, {
            'start': (now + timedelta(days=2)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(days=3)).replace(microsecond=0).isoformat(' '),
            'allday': True,
        }]
        request = self.url_open(
            "/appointment/appointment_type/create_custom",
            data=json.dumps({
                'params': {
                    'slots': unique_slots,
                    'context': {
                        'default_assign_method': 'time_resource',
                    },
                }
            }),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', dict())
        self.assertTrue(result.get('appointment_type_id'), 'The request returns the id of the custom appointment type')

        appointment_type = self.env['appointment.type'].browse(result['appointment_type_id'])
        # The default context fields should be ignored as the fields are not whitelisted
        self.assertEqual(appointment_type.assign_method, 'resource_time')

    def test_share_appointment_type(self):
        self._create_invite_test_data()
        self.authenticate(None, None)
        res = self.url_open(self.invite_apt_type_bxls_2days.book_url)
        self.assertEqual(res.status_code, 200, "Response should = OK")

    def test_share_appointment_type_multi(self):
        self._create_invite_test_data()
        self.authenticate(None, None)
        res = self.url_open(self.invite_all_apts.book_url)
        self.assertEqual(res.status_code, 200, "Response should = OK")


    @users('apt_manager')
    @freeze_time('2022-02-15T14:00:00')
    def test_action_meeting_from_appointment_type(self):
        """Check values of the action of viewing meetings from clicking an appointment type.

        Example: Click on 'View Meetings' from an appointment type with no resource management -> open gantt
        """
        now = datetime.now()
        appointment_types = self.env['appointment.type'].create([{
            'name': 'Type Test Actions Users',
            'schedule_based_on': 'users',
            'staff_user_ids': (self.apt_manager | self.std_user).ids,
        }, {
            'name': 'Type Test Actions Resource',
            'schedule_based_on': 'resources',
            'resource_ids': [Command.create({'name': 'Test Resource', 'capacity': 1})]
        }])
        # create an event to test smart scale
        self.env['calendar.event'].create({
            'name': 'Next Month Appointment',
            'appointment_type_id': appointment_types[1].id,
            'start': datetime(2022, 3, 1),
            'stop': datetime(2022, 3, 1, 1),
        })
        self.maxDiff = None
        expected_xml_ids = ['appointment.calendar_event_action_view_bookings_users',
                            'appointment.calendar_event_action_view_bookings_resources']
        expected_views_orders = [['gantt', 'calendar'], ['gantt', 'calendar']]
        expected_contexts = [{
            'appointment_default_assign_user_attendees': True,
            'default_scale': 'day',
            'default_appointment_type_id': appointment_types[0].id,
            'default_duration': appointment_types[0].appointment_duration,
            'search_default_appointment_type_id': appointment_types[0].id,
            'default_mode': 'week',
            'default_partner_ids': [],
            'default_start_date': now,
            'initial_date': now,
        }, {
            'appointment_booking_gantt_domain': [('appointment_resource_ids', '!=', False)],
            'appointment_default_assign_user_attendees': False,
            'default_scale': 'day',
            'default_appointment_type_id': appointment_types[1].id,
            'default_duration': appointment_types[1].appointment_duration,
            'search_default_appointment_type_id': appointment_types[1].id,
            'default_mode': 'month',
            'default_partner_ids': [],
            'default_resource_total_capacity_reserved': 1,
            'default_start_date': now,
            'initial_date': datetime(2022, 3, 1),
        }]
        for (appointment_type, expected_views_order,
             expected_context, xml_id) in zip(appointment_types, expected_views_orders, expected_contexts, expected_xml_ids):
            with self.subTest(appointment_type=appointment_type):
                action = appointment_type.action_calendar_meetings()
                views_order = [view_id_type[1] for view_id_type in action['views'][:len(expected_views_order)]]
                self.assertEqual(views_order, expected_views_order)
                self.assertDictEqual(action['context'], expected_context)
                self.assertEqual(action['xml_id'], xml_id)


    @users('apt_manager')
    def test_appointment_meeting_url(self):
        """ Test if a meeting linked to an appointment has the right meeting URL no matter its location. """
        CalendarEvent = self.env['calendar.event']
        self.authenticate(self.env.user.login, self.env.user.login)
        datetime_format = "%Y-%m-%d %H:%M:%S"
        discuss_route = CalendarEvent.DISCUSS_ROUTE

        appointment_with_discuss_videocall_source = self.env['appointment.type'].create({
            'name': 'Schedule a Demo with Odoo Discuss URL',
            'staff_user_ids': self.staff_user_bxls,
            'event_videocall_source': 'discuss',
        })
        appointment_without_videocall_source = self.env['appointment.type'].create({
            'name': 'Schedule a Demo without meeting URL',
            'staff_user_ids': self.staff_user_bxls,
            'event_videocall_source': False,
        })

        online_meeting = {
            'duration_str': '1.0',
            'datetime_str': '2022-07-04 12:30:00',
            'staff_user_id': self.staff_user_bxls.id,
            'name': 'Online Meeting',
            'phone': '2025550999',
            'email': 'test1@test.example.com',
            'csrf_token': http.Request.csrf_token(self)
        }
        meeting_with_location = {
            'duration_str': '1.0',
            'datetime_str': '2022-07-05 10:30:00',
            'staff_user_id': self.staff_user_bxls.id,
            'name': 'Meeting with location',
            'phone': '2025550888',
            'email': 'test2@test.example.com',
            'csrf_token': http.Request.csrf_token(self),
        }

        cases = [
            (appointment_with_discuss_videocall_source, online_meeting, True),
            (appointment_without_videocall_source, online_meeting, False),
            (appointment_with_discuss_videocall_source, meeting_with_location, True),
            (appointment_without_videocall_source, meeting_with_location, False),
        ]

        for appointment, appointment_data, expect_discuss in cases:
            # Prevent booking the same slot
            appt_datetime = datetime.strptime(appointment_data.get('datetime_str'), datetime_format)
            new_appt_datetime = pytz.timezone(appointment.appointment_tz).localize(appt_datetime) + timedelta(hours=1)
            appointment_data.update({'datetime_str': new_appt_datetime.strftime(datetime_format)})

            if appointment_data.get('name') == 'Meeting with location':
                appointment.update({'location_id': self.staff_user_bxls.partner_id.id})
            url = f"/appointment/{appointment.id}/submit"
            res = self.url_open(url, data=appointment_data)
            self.assertEqual(res.status_code, 200, "Response should = OK")
            event = CalendarEvent.search([('appointment_type_id', '=', appointment.id), ('start', '=', new_appt_datetime.astimezone(pytz.utc))])
            self.assertIn(event.access_token, res.url)
            with self.subTest(expect_discuss=expect_discuss, access_token=event.access_token):
                if expect_discuss:
                    self.assertIn(discuss_route, event.videocall_location,
                        "Should have discuss link as videocall_location as the appointment type videocall source is set to Odoo Discuss")
                else:
                    self.assertFalse(event.videocall_location,
                        "Should not have a videocall_location as the appointment type doesn't have any videocall source")

    @freeze_time('2022-02-13')
    @users('apt_manager')
    def test_appointment_crossing_manual_confirmation_treshold(self):
        """ Test that when crossing over the manual confirmation treshold, the attendees are not confirmed """
        self.assertFalse(self.apt_type_resource.meeting_ids)  # Assert initial data
        self.authenticate(self.env.user.login, self.env.user.login)
        resource = self.env['appointment.resource'].sudo().create([{
            "appointment_type_ids": self.apt_type_resource.ids,
            "capacity": 4,
            "name": "Resource",
        }])
        self.apt_type_resource.sudo().write({
            "appointment_manual_confirmation": True,
            "resource_manual_confirmation_percentage": 0.5,  # Set Manual Confirmation at 50%
        })
        appointment_data = {
            "asked_capacity": 4,
            "available_resource_ids": [resource.id],
            "csrf_token": http.Request.csrf_token(self),
            "datetime_str": "2022-02-14 15:00:00",
            "duration_str": "1.0",
            "email": "test@test.example.com",
            "name": "Online Meeting",
            "phone": "2025550999",
        }

        url = f"/appointment/{self.apt_type_resource.id}/submit"
        res = self.url_open(url, data=appointment_data)
        self.assertEqual(res.status_code, 200, "Response should = OK")

        meeting = self.env["calendar.event"].search([("appointment_type_id", "=", self.apt_type_resource.id)])
        self.assertTrue(meeting)
        self.assertEqual(meeting.appointment_status, "request")
        self.assertEqual(meeting.attendee_ids.state, "accepted",
            "Crossing over the manual confirmation percentage should confirm the attendees immediately.")
        self.assertEqual(meeting.resource_total_capacity_reserved, 4)

    @freeze_time('2022-02-14')
    @users('apt_manager')
    def test_appointment_staff_user_manual_confirmation(self):
        """ Check that appointment and attendee status are correctly
        set based on the appointment_manual_confirmation field"""
        self.authenticate(self.env.user.login, self.env.user.login)
        event_values = {
            'csrf_token': http.Request.csrf_token(self),
            'datetime_str': '2022-02-14 11:00:00',
            'duration_str': '1.0',
            'email': 'test1@test.example.com',
            'name': 'Meeting Test',
            'phone': '2025550999',
            'staff_user_id': self.staff_user_bxls.id,
        }
        self.assertFalse(self.apt_type_bxls_2days.appointment_manual_confirmation)
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", event_values)
        self.assertEqual(res.status_code, 200, "Response should be OK")
        self.assertEqual(len(self.apt_type_bxls_2days.meeting_ids), 1)
        self.assertEqual(self.apt_type_bxls_2days.meeting_ids[0].appointment_status, "booked")
        self.assertTrue(all(attendee.state == 'accepted' for attendee in self.apt_type_bxls_2days.meeting_ids.attendee_ids))

        self.apt_type_bxls_2days.appointment_manual_confirmation = True
        event_values['datetime_str'] = '2022-02-14 12:00:00'
        res = self.url_open(f"/appointment/{self.apt_type_bxls_2days.id}/submit", event_values)
        self.assertEqual(res.status_code, 200, "Response should be OK")
        self.assertEqual(len(self.apt_type_bxls_2days.meeting_ids), 2)
        self.assertEqual(self.apt_type_bxls_2days.meeting_ids[0].appointment_status, "request")
        self.assertTrue(all(attendee.state == 'accepted' for attendee in self.apt_type_bxls_2days.meeting_ids.attendee_ids))

    @freeze_time('2022-02-14T7:00:00')
    def test_get_appointment_type_page_view(self):
        """ Test if the appointment_type_page always shows available slots if there are some. """
        now = self.reference_monday
        slot_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)

        staff_users = self.user_employee | self.user_admin
        appointment_type = self.env['appointment.type'].create([{
            'name': 'Type Test Appointment View',
            'schedule_based_on': 'users',
            'staff_user_ids': staff_users.ids,
            'min_schedule_hours': 1.0,
            'max_schedule_days': 5,
            'slot_ids': [(0, 0, {
                'weekday': str(slot_time.isoweekday()),
                'start_hour': slot_time.hour,
                'end_hour': slot_time.hour + 1,
            })],
            'avatars_display': 'hide',
            'assign_method': 'resource_time',
        }])

        invite = self.env['appointment.invite'].create({
            'appointment_type_ids': appointment_type.ids,
        })

        def render_appointment_page():
            page = self.url_open(invite.book_url)
            arch = html.fromstring(page.text)

            [slots_form] = arch.xpath("//form[@id='slots_form']")
            [selected_user_option] = slots_form.xpath("//*[@id='selectStaffUser']/*[@selected]")
            [slots_calendar] = arch.xpath("//*[@id='calendar']")

            return slots_form, selected_user_option, slots_calendar

        slots_form, selected_user_option, slots_calendar = render_appointment_page()
        self.assertIn(
            int(selected_user_option.attrib['value']),
            staff_users.ids,
            f"Selected user must be one of {staff_users.ids}"
        )
        self.assertFalse(
            'd-none' in slots_form.getparent().attrib['class'],
            "Staff user selector should be visible")
        self.assertTrue(
            slots_calendar.getchildren(),
            "Slots calendar should be visible")

        # create an event to make the first staff user busy and remove its available slots
        selected_staff_user = self.env['res.users'].browse(int(selected_user_option.attrib['value']))
        remaining_staff_user = staff_users - selected_staff_user
        self._create_meetings(selected_staff_user, [(slot_time, slot_time + timedelta(hours=1), True)])

        slots_form, selected_user_option, slots_calendar = render_appointment_page()
        self.assertEqual(
            int(selected_user_option.attrib['value']),
            remaining_staff_user.id,
            f"Selected user should be user with ID: {remaining_staff_user.id}")
        self.assertFalse(
            'd-none' in slots_form.getparent().attrib['class'],
            "Staff user selector should be visible")
        self.assertTrue(
            slots_calendar.getchildren(),
            "Slots calendar should be visible")

        # create another event to make both staff user busy and remove all slots
        self._create_meetings(remaining_staff_user, [(slot_time, slot_time + timedelta(hours=1), True)])
        slots_form, _, slots_calendar = render_appointment_page()
        self.assertTrue(
            'd-none' in slots_form.getparent().attrib['class'],
            "Staff user selector should not be visible")
        self.assertFalse(
            slots_calendar.getchildren(),
            "Slots calendar should not be visible")

@tagged('appointment_ui', '-at_install', 'post_install')
class CalendarTest(AppointmentUICommon):

    def test_meeting_accept_authenticated(self):
        event = self.env["calendar.event"].create(
            {"name": "Doom's day",
             "start": datetime(2019, 10, 25, 8, 0),
             "stop": datetime(2019, 10, 27, 18, 0),
             "partner_ids": [(4, self.std_user.partner_id.id)],
            }
        )
        token = event.attendee_ids[0].access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, event.id)
        self.authenticate(self.std_user.login, self.std_user.login)
        res = self.url_open(url)

        self.assertEqual(res.status_code, 200, "Response should = OK")
        event.attendee_ids[0].invalidate_recordset()
        self.assertEqual(event.attendee_ids[0].state, "accepted", "Attendee should have accepted")

    def test_meeting_accept_unauthenticated(self):
        event = self.env["calendar.event"].create(
            {"name": "Doom's day",
             "start": datetime(2019, 10, 25, 8, 0),
             "stop": datetime(2019, 10, 27, 18, 0),
             "partner_ids": [(4, self.std_user.partner_id.id)],
            }
        )
        token = event.attendee_ids[0].access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, event.id)
        res = self.url_open(url)

        self.assertEqual(res.status_code, 200, "Response should = OK")
        event.attendee_ids[0].invalidate_recordset()
        self.assertEqual(event.attendee_ids[0].state, "accepted", "Attendee should have accepted")

    @freeze_time('2023, 11, 22')
    def test_meeting_booker_cancel(self):
        """ Test that when appointment Booker cancels the meeting then the event should
        be archived.
        """
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.apt_type_bxls_2days.write({'is_published': 'True'})
        event = self.env['calendar.event'].create({
            'name': 'Test-Meeting 2',
            'user_id': self.portal_user.id,
            'appointment_booker_id': self.portal_user.partner_id.id,
            'start': datetime(2023, 11, 23, 9, 0),
            'stop':  datetime(2023, 11, 23, 10, 0),
            'partner_ids': [
                (4, self.staff_user_nz.partner_id.id),
                (4, self.staff_user_aust.partner_id.id),
                (4, self.apt_manager.partner_id.id),
                (4, self.portal_user.partner_id.id),
            ],
            'appointment_type_id': self.apt_type_bxls_2days.id,
        })
        cancel_meeting_data = {
            'access_token': event.access_token,
            'partner_id': self.portal_user.partner_id.id,
            'csrf_token': http.Request.csrf_token(self),
        }
        cancel_meeting_url = f"/calendar/{event.access_token}/cancel"
        res = self.url_open(cancel_meeting_url, data=cancel_meeting_data)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(event.active)

    @freeze_time('2023, 11, 22')
    def test_meeting_cancel_no_partner(self):
        """ Test cancellation of meeting with no partner. """
        self.authenticate(None, None)
        self.apt_type_bxls_2days.write({'is_published': 'True'})
        event = self.env['calendar.event'].create({
            'name': 'Test-Meeting 1',
            'user_id': self.staff_user_aust.id,
            'appointment_booker_id': self.staff_user_nz.partner_id.id,
            'start': datetime(2023, 11, 23, 8, 0),
            'stop':  datetime(2023, 11, 23, 9, 0),
            'partner_ids':  [
                (4, self.staff_user_nz.partner_id.id),
                (4, self.portal_user.partner_id.id),
                (4, self.staff_user_aust.partner_id.id),
            ],
            'appointment_type_id': self.apt_type_bxls_2days.id,
        })
        cancel_meeting_data = {
            'access_token': event.access_token,
            'csrf_token': http.Request.csrf_token(self),
        }
        cancel_meeting_url = f"/calendar/{event.access_token}/cancel"
        res = self.url_open(cancel_meeting_url, data=cancel_meeting_data)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(event.active)
