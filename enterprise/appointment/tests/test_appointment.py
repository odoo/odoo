# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import date, datetime, timedelta, timezone
from freezegun import freeze_time
from werkzeug.urls import url_encode, url_join

import odoo
from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger
from odoo.fields import Command


@tagged('appointment_slots')
class AppointmentTest(AppointmentCommon, HttpCaseWithUserDemo):

    @freeze_time('2023-12-12')
    @users('apt_manager')
    def test_appointment_availability_after_utc_conversion(self):
        """ Check that when an event starts the day before,
            it doesn't show the date as available for the user.
            ie: In the brussels TZ, when placing an event on the 15 dec at 00:15 to 18:00,
            the event is stored in the UTC TZ on the 14 dec at 23:15 to 17:00
            Because the event start on another day, the 15th was displayed as available.
        """
        staff_user = self.staff_users[0]
        week_days = [0, 1, 2]
        # The user works on mondays, tuesdays, and wednesdays
        # Only one hour slot per weekday
        self.apt_type_bxls_2days.slot_ids = [(5, 0)] + [(0, 0, {
            'weekday': str(week_day + 1),
            'start_hour': 8,
            'end_hour': 9,
        }) for week_day in week_days]

        # Available on the 12, 13, 18, 19, 20, 25, 26, 27 dec
        max_available_slots = 8
        test_data = [
            # Test 1, after UTC
            # Brussels TZ: 2023-12-19 00:15 to 2023-12-19 18:00 => same day
            # UTC TZ:      2023-12-18 23:15 to 2023-12-19 17:00 => different day
            (
                datetime(2023, 12, 18, 23, 15),
                datetime(2023, 12, 19, 17, 0),
                max_available_slots - 1,
                {date(2023, 12, 19): []},
            ),
            # Test 2, before UTC
            # New York TZ: 2023-12-18 10:00 to 2023-12-18 22:00 => same day
            # UTC TZ:      2023-12-18 15:00 to 2023-12-19 03:00 => different day
            (
                datetime(2023, 12, 18, 15, 0),
                datetime(2023, 12, 19, 3, 0),
                max_available_slots - 0,
                {},
            ),
        ]
        global_slots_startdate = date(2023, 11, 26)
        global_slots_enddate = date(2024, 1, 6)
        slots_startdate = date(2023, 12, 12)
        slots_enddate = slots_startdate + timedelta(days=15)
        for start, stop, nb_available_slots, slots_day_specific in test_data:
            with self.subTest(start=start, stop=stop, nb_available_slots=nb_available_slots):
                event = self.env["calendar.event"].create([
                    {
                        "name": "event-1",
                        "start": start,
                        "stop": stop,
                        "show_as": 'busy',
                        "partner_ids": staff_user.partner_id.ids,
                        "attendee_ids": [(0, 0, {
                            "state": "accepted",
                            "availability": "busy",
                            "partner_id": staff_user.partner_id.id,
                        })],
                    },
                ])
                slots = self.apt_type_bxls_2days._get_appointment_slots(timezone='Europe/Brussels', filter_users=staff_user)
                self.assertSlots(
                    slots,
                    [{'name_formated': 'December 2023',
                      'month_date': datetime(2023, 12, 1),
                      'weeks_count': 6,
                      }
                     ],
                    {'startdate': global_slots_startdate,
                     'enddate': global_slots_enddate,
                     'slots_startdate': slots_startdate,
                     'slots_enddate': slots_enddate,
                     'slots_start_hours': [8],
                     'slots_weekdays_nowork': range(3, 7),
                     'slots_day_specific': slots_day_specific,
                     }
                )
                available_slots = self._filter_appointment_slots(slots, filter_weekdays=week_days)
                self.assertEqual(nb_available_slots, len(available_slots))
                event.unlink()

    @freeze_time('2023-01-6')
    @users('apt_manager')
    def test_appointment_availability_with_show_as(self):
        """ Checks that if a normal event and custom event both set at the same time but
        the normal event is set as free then the custom meeting should be available and
        available_unique_slots will contains only available slots """

        employee = self.staff_users[0]
        self.env["calendar.event"].create([
            {
                "name": "event-1",
                "start": datetime(2023, 6, 5, 10, 10),
                "stop": datetime(2023, 6, 5, 11, 11),
                "show_as": 'free',
                "partner_ids": [(Command.set(employee.partner_id.ids))],
                "attendee_ids": [(0, 0, {
                    "state": "accepted",
                    "availability": "free",
                    "partner_id": employee.partner_id.id,
                })],
            }, {
                "name": "event-2",
                "start": datetime(2023, 6, 5, 12, 0),
                "stop": datetime(2023, 6, 5, 13, 0),
                "show_as": 'busy',
                "partner_ids": [(Command.set(employee.partner_id.ids))],
                "attendee_ids": [(0, 0, {
                    "state": "accepted",
                    "availability": "busy",
                    "partner_id": employee.partner_id.id,
                })],
            },
        ])

        unique_slots = [{
            'allday': False,
            'start_datetime': datetime(2023, 6, 5, 10, 10),
            'end_datetime': datetime(2023, 6, 5, 11, 11),
        }, {
            'allday': False,
            'start_datetime': datetime(2023, 6, 5, 12, 0),
            'end_datetime': datetime(2023, 6, 5, 13, 0),
        }]

        hour_fifty_float_repr_A = 1.8333333333333335
        hour_fifty_float_repr_B = 1.8333333333333333

        apt_types = self.env['appointment.type'].create([
            {
                'category': 'custom',
                'name': 'Custom Meeting 1',
                'staff_user_ids': [(4, employee.id)],
                'slot_ids': [(0, 0, {
                    'allday': slot['allday'],
                    'end_datetime': slot['end_datetime'],
                    'slot_type': 'unique',
                    'start_datetime': slot['start_datetime'],
                    }) for slot in unique_slots
                ],
            }, {
                'category': 'custom',
                'name': 'Custom Meeting 2',
                'staff_user_ids': [(4, employee.id)],
                'slot_ids': [(0, 0, {
                    'allday': unique_slots[1]['allday'],
                    'end_datetime': unique_slots[1]['end_datetime'],
                    'slot_type': 'unique',
                    'start_datetime': unique_slots[1]['start_datetime'],
                    })
                ],
            }, {
                'category': 'recurring',
                'name': 'Recurring Meeting 3',
                'staff_user_ids': [(4, employee.id)],
                'appointment_duration': hour_fifty_float_repr_A,  # float presenting 1h 50min
                'appointment_tz': 'UTC',
                'slot_ids': [
                    (0, False, {
                        'weekday': '1',  # Monday
                        'start_hour': 8,
                        'end_hour': 17,
                        }
                    )
                ]
            },
        ])

        self.assertTrue(
            apt_types[-1]._check_appointment_is_valid_slot(
                employee,
                0,
                0,
                'UTC',
                datetime(2023, 1, 9, 8, 0, tzinfo=timezone.utc),  # First monday in the future
                duration=hour_fifty_float_repr_B
            ),
            "Small imprecision on float value for duration should not impact slot validity"
        )

        slots = apt_types[0]._get_appointment_slots('UTC')
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(6, 2023)],
            filter_users=employee)

        self.assertEqual(len(available_unique_slots), 1)

        for unique_slot, apt_type, is_available in zip(unique_slots, apt_types, [True, False]):
            duration = (unique_slot['end_datetime'] - unique_slot['start_datetime']).total_seconds() / 3600
            self.assertEqual(
                apt_type._check_appointment_is_valid_slot(
                    employee,
                    0,
                    0,
                    'UTC',
                    unique_slot['start_datetime'],
                    duration
                ),
                is_available
            )

            self.assertEqual(
                employee.partner_id.calendar_verify_availability(
                    unique_slot['start_datetime'],
                    unique_slot['end_datetime'],
                ),
                is_available
            )

    @freeze_time('2025-05-19')
    def test_appointment_not_blocked_by_nextday_allday_event(self):
        """Ensure Monday 7-8:30 PM (local) is not blocked by a Tuesday all-day event,
            even if both overlap on May 20 UTC due to time zone conversion.
        """
        self.staff_user_bxls.tz = 'America/Chicago'
        local_tz = pytz.timezone(self.staff_user_bxls.tz)

        # Monday 7:00 PM → 8:30 PM (local) converted to UTC - start time is Tuesday 0:0 UTC and end time is 1:30 UTC
        slot_start_utc = local_tz.localize(datetime(2025, 5, 19, 19, 0)).astimezone(pytz.utc).replace(tzinfo=None)
        slot_end_utc = local_tz.localize(datetime(2025, 5, 19, 20, 30)).astimezone(pytz.utc).replace(tzinfo=None)

        busy_day = datetime(2025, 5, 20, 0, 0)  # 2025-5-20 is the following Tuesday
        self.env['calendar.event'].create({
            'name': "All-Day Tuesday",
            'start': busy_day,
            'stop': busy_day + timedelta(days=1),
            'allday': True,
            'show_as': 'busy',
            'partner_ids': [self.staff_user_bxls.partner_id.id],
            'user_id': self.staff_user_bxls.id,
            'attendee_ids': [Command.create({
                'state': 'accepted',
                'availability': 'busy',
                'partner_id': self.staff_user_bxls.partner_id.id,
                }),
            ],
        })
        self.assertTrue(
            self.staff_user_bxls.partner_id.with_context(tz='America/Chicago').calendar_verify_availability(slot_start_utc, slot_end_utc),
            "Time slots should not be blocked by next-day all-day events."
        )

    @users('apt_manager')
    def test_appointment_type_create_anytime(self):
        # Any Time: only 1 / employee
        apt_type = self.env['appointment.type'].create({
            'category': 'anytime',
            'name': 'Any time on me',
        })
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)

        # should be able to create 2 'anytime' appointment types at once on different users
        self.env['appointment.type'].create([{
            'category': 'anytime',
            'name': 'Any on staff user',
            'staff_user_ids': [(4, staff_user.id)],
        } for staff_user in self.staff_users])

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'category': 'anytime',
                'name': 'Any time on me, duplicate',
            })

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'name': 'Any time without employees',
                'category': 'anytime',
                'staff_user_ids': False
            })

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'name': 'Any time with multiple employees',
                'category': 'anytime',
                'staff_user_ids': [(6, 0, self.staff_users.ids)]
            })

    @users('apt_manager')
    def test_appointment_type_create_custom(self):
        # Custom: current user set as default
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom without user',
        })
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)

        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'staff_user_ids': [(4, self.staff_users[0].id)],
            'name': 'Custom with user',
        })
        self.assertEqual(apt_type.staff_user_ids, self.staff_users[0])

        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'staff_user_ids': self.staff_users.ids,
            'name': 'Custom with users',
        })
        self.assertEqual(apt_type.staff_user_ids, self.staff_users)

    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_appointment_slot_start_end_hour_auto_correction(self):
        """ Test the autocorrection of invalid intervals [start_hour, end_hour]. """
        appt_type = self.env['appointment.type'].create({
            'category': 'recurring',
            'name': 'Schedule a demo',
            'appointment_duration': 1,
            'slot_ids': [(0, 0, {
                'weekday': '1',  # Monday
                'start_hour': 9,
                'end_hour': 17,
            })],
        })
        appt_form = Form(appt_type)

        # invalid interval, no adaptation because start_hour is not changed
        with self.assertRaises(ValidationError):
            with appt_form.slot_ids.edit(0) as slot_form:
                slot_form.end_hour = 8
            appt_form.save()

        # invalid interval, adapted because start_hour is changed
        with appt_form.slot_ids.edit(0) as slot_form:
            slot_form.start_hour = 18
            self.assertEqual(slot_form.start_hour, 18)
            self.assertEqual(slot_form.end_hour, 19)
        appt_form.save()

        # empty interval, adapted because start_hour is changed
        with appt_form.slot_ids.edit(0) as slot_form:
            slot_form.start_hour = 19
            self.assertEqual(slot_form.start_hour, 19)
            self.assertEqual(slot_form.end_hour, 20)
        appt_form.save()

        # invalid interval, end_hour not adapted [23.5, 19] because it will exceed 24
        with self.assertRaises(ValidationError):
            with appt_form.slot_ids.edit(0) as slot_form:
                slot_form.start_hour = 23.5
            appt_form.save()

    def test_generate_slots_until_midnight(self):
        """ Generate recurring slots until midnight. """
        appt_type = self.env['appointment.type'].create({
            'category': 'recurring',
            'name': 'Schedule a demo',
            'max_schedule_days': 1,
            'appointment_duration': 1,
            'appointment_tz': 'Europe/Brussels',
            'slot_ids': [(0, 0, {
                'weekday': '1',  # Monday
                'start_hour': 18,
                'end_hour': 0,
            })],
            'staff_user_ids': [(4, self.staff_user_bxls.id)],
        }).with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = appt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
              }
             ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_start_hours': [18, 19, 20, 21, 22, 23],
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_enddate': self.reference_monday.date(),  # only test that day
             }
        )


    @users('apt_manager')
    def test_appointment_type_custom_badge(self):
        """ Check that the number of previous and next slots in the badge are correctly based on availability """
        reference_start = self.reference_monday.replace(microsecond=0)
        unique_slots = [{
            'allday': True,
            'end_datetime': reference_start + timedelta(days=delta_day + 1),
            'slot_type': 'unique',
            'start_datetime': reference_start + timedelta(days=delta_day),
        } for delta_day in (0, 1, 31, 62, 63)]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom Appointment Type',
            'slot_ids': [(5, 0)] + [(0, 0, slot) for slot in unique_slots],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        nb_february_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_users=self.apt_manager))
        nb_march_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(3, 2022)],
            filter_users=self.apt_manager))
        nb_april_slots = len(self._filter_appointment_slots(
            slots, filter_months=[(4, 2022)],
            filter_users=self.apt_manager))

        # February month
        self.assertEqual(slots[0]['nb_slots_previous_months'], 0)
        self.assertEqual(slots[0]['nb_slots_next_months'], nb_march_slots + nb_april_slots)

        # March month
        self.assertEqual(slots[1]['nb_slots_previous_months'], nb_february_slots)
        self.assertEqual(slots[1]['nb_slots_next_months'], nb_april_slots)

        # April month
        self.assertEqual(slots[2]['nb_slots_previous_months'], nb_february_slots + nb_march_slots)
        self.assertEqual(slots[2]['nb_slots_next_months'], 0)

        # Create a meeting during the duration of the first slot
        self._create_meetings(self.apt_manager, [(
            reference_start + timedelta(hours=2),
            reference_start + timedelta(hours=3),
            False,
        )])

        previous_nb_feb_slots = nb_february_slots

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        nb_february_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_users=self.apt_manager))
        nb_march_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(3, 2022)],
            filter_users=self.apt_manager))
        nb_april_slots = len(self._filter_appointment_slots(
            slots, filter_months=[(4, 2022)],
            filter_users=self.apt_manager))

        # February month
        self.assertEqual(slots[0]['nb_slots_previous_months'], 0)
        self.assertEqual(slots[0]['nb_slots_next_months'], nb_march_slots + nb_april_slots)
        self.assertEqual(nb_february_slots, previous_nb_feb_slots - 1)

        # March month
        self.assertEqual(slots[1]['nb_slots_previous_months'], nb_february_slots)
        self.assertEqual(slots[1]['nb_slots_next_months'], nb_april_slots)

        # April month
        self.assertEqual(slots[2]['nb_slots_previous_months'], nb_february_slots + nb_march_slots)
        self.assertEqual(slots[2]['nb_slots_next_months'], 0)

    @freeze_time('2023-01-9')
    def test_booking_validity(self):
        """
        When confirming an appointment, we must recheck that it is indeed a valid slot,
        because the user can modify the date URL parameter used to book the appointment.
        We make sure the date is a valid slot, not outside of those specified by the employee,
        and that it's not an old valid slot (a slot that is valid, but it's in the past,
        so we shouldn't be able to book for a date that has already passed)
        """
        # add the timezone of the visitor on the session (same as appointment to simplify)
        session = self.authenticate(None, None)
        session['timezone'] = self.apt_type_bxls_2days.appointment_tz
        odoo.http.root.session_store.save(session)
        appointment = self.apt_type_bxls_2days
        appointment_invite = self.env['appointment.invite'].create({'appointment_type_ids': appointment.ids})
        appointment_url = url_join(appointment.get_base_url(), '/appointment/%s' % appointment.id)
        appointment_info_url = "%s/info?" % appointment_url
        url_inside_of_slot = appointment_info_url + url_encode({
            'staff_user_id': self.staff_user_bxls.id,
            'date_time': datetime(2023, 1, 9, 9, 0),  # 9/01/2023 is a Monday, there is a slot at 9:00
            'duration': 1,
            **appointment_invite._get_redirect_url_parameters(),
        })
        response = self.url_open(url_inside_of_slot)
        self.assertEqual(response.status_code, 200, "Response should be Ok (200)")
        url_outside_of_slot = appointment_info_url + url_encode({
            'staff_user_id': self.staff_user_bxls.id,
            'date_time': datetime(2023, 1, 9, 22, 0),  # 9/01/2023 is a Monday, there is no slot at 22:00
            'duration': 1,
            **appointment_invite._get_redirect_url_parameters(),
        })
        response = self.url_open(url_outside_of_slot)
        self.assertEqual(response.status_code, 404, "Response should be Page Not Found (404)")
        url_inactive_past_slot = appointment_info_url + url_encode({
            'staff_user_id': self.staff_user_bxls.id,
            'date_time': datetime(2023, 1, 2, 22, 0),
            # 2/01/2023 is a Monday, there is a slot at 9:00, but that Monday has already passed
            'duration': 1,
            **appointment_invite._get_redirect_url_parameters(),
        })
        response = self.url_open(url_inactive_past_slot)
        self.assertEqual(response.status_code, 404, "Response should be Page Not Found (404)")

    @freeze_time('2023-04-23')
    def test_booking_validity_timezone(self):
        """
        When the utc offset of the timezone is large, it is possible that the day of the week no longer corresponds.
        It is necessary to take this into account when checking the slots.
        """
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'Pacific/Auckland',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'location_id': self.staff_user_nz.partner_id.id,
            'name': 'New Zealand Appointment',
            'max_schedule_days': 15,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'slot_ids': [
                (0, False, {'weekday': weekday,
                            'start_hour': hour,
                            'end_hour': hour + 1,
                           })
                for weekday in ['1']
                for hour in range(9, 12)
            ],
            'staff_user_ids': [(4, self.staff_user_nz.id)],
        })
        session = self.authenticate(None, None)
        session['timezone'] = appointment.appointment_tz
        odoo.http.root.session_store.save(session)
        appointment_invite = self.env['appointment.invite'].create({'appointment_type_ids': appointment.ids})
        appointment_url = url_join(appointment.get_base_url(), '/appointment/%s' % appointment.id)
        appointment_info_url = "%s/info?" % appointment_url
        url = appointment_info_url + url_encode({
            'staff_user_id': self.staff_user_nz.id,
            'date_time': datetime(2023, 4, 24, 9, 0),
            'duration': 1,
            **appointment_invite._get_redirect_url_parameters(),
        })
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200, "Response should be Ok (200)")

    def test_exclude_all_day_events(self):
        """ Ensure appointment slots don't overlap with "busy" allday events. """
        staff_user = self.staff_users[0]
        valentime = datetime(2022, 2, 14, 0, 0)  # 2022-02-14 is a Monday

        slots = self.apt_type_bxls_2days._get_appointment_slots(
            self.apt_type_bxls_2days.appointment_tz,
            reference_date=valentime,
        )
        slot = slots[0]['weeks'][2][1]
        self.assertEqual(slot['day'], valentime.date())
        self.assertTrue(slot['slots'], "Should be available on 2022-02-14")

        self.env['calendar.event'].with_user(staff_user).create({
            'name': "Valentine's day",
            'start': valentime,
            'stop': valentime,
            'allday': True,
            'show_as': 'busy',
            'attendee_ids': [(0, 0, {
                'state': 'accepted',
                'availability': 'busy',
                'partner_id': staff_user.partner_id.id,
            })],
        })

        slots = self.apt_type_bxls_2days._get_appointment_slots(
            self.apt_type_bxls_2days.appointment_tz,
            reference_date=valentime,
        )
        slot = slots[0]['weeks'][2][1]
        self.assertEqual(slot['day'], valentime.date())
        self.assertFalse(slot['slots'], "Shouldn't be available on 2022-02-14")

    @users('apt_manager')
    def test_customer_event_description(self):
        """Check calendar file description and summary generation."""
        appointment_type = self.apt_type_bxls_2days
        host_partner = self.apt_manager.partner_id
        appointment_type.message_confirmation = '<p>Please try to be there <strong>5 minutes</strong> before the time.<p><br>Thank you.'
        appointment_question = self.env['appointment.question'].create({
            'appointment_type_id': appointment_type.id,
            'name': 'How are you ?',
            'question_type': 'char',
        })
        appointment_answer_input_values = {
            'appointment_type_id': appointment_type.id,
            'question_id': appointment_question.id,
            'value_text_box': 'I am Good',
        }
        attendee = self.env['res.partner'].sudo().create({
            'name': '<p>John Doe</p>',
            'email': 'john@example.com',
            'phone': '123456789',
        })
        extra_attendee = self.env['res.partner'].sudo().create({
            'name': 'Jean',
            'email': 'jean@example.com',
            'phone': '888888888',
        })
        host_partner.phone = '+32456111111'
        appointment = self.env['calendar.event'].create({
            'name': '%s with %s' % (appointment_type.name, attendee.name),
            'start': datetime.now(),
            'start_date': datetime.now(),
            'stop': datetime.now() + timedelta(hours=1),
            'allday': False,
            'duration': appointment_type.appointment_duration,
            'location': appointment_type.location,
            'partner_ids': [odoo.Command.link(partner.id) for partner in [attendee, host_partner, extra_attendee]],
            'appointment_booker_id': attendee.id,
            'appointment_type_id': appointment_type.id,
            'appointment_answer_input_ids': [(0, 0, appointment_answer_input_values)],
            'user_id': self.apt_manager.id,
        })
        url = f"{appointment_type.get_base_url()}/calendar/view/{appointment.access_token}"
        description = (
            '<div><span>Contact Details</span><br><span>&lt;p&gt;John Doe&lt;/p&gt; - john@example.com - 123456789</span>'
            '<br><span>Appointment Manager - apt_manager@test.example.com - +32456111111</span><br><span>Jean - jean@example.com</span>'
            '</div><br><div><span>Questions</span><br><span>How are you ?: I am Good</span></div><br>'
            '<p>Please try to be there <strong>5 minutes</strong> before the time.</p><p><br>Thank you.</p>'
            '<span>Need to reschedule? <a href=%s>Click here</a></span>'
        ) % (url)
        self.assertEqual(appointment._get_customer_description(), description)

        # Test summary for all appointment types
        resource_appointment = self.apt_type_resource
        resource_event = self.env['calendar.event'].create({
            'name': '%s - %s' % (resource_appointment.name, attendee.name),
            'start': datetime.now(),
            'stop': datetime.now() + timedelta(hours=1),
            'appointment_type_id': resource_appointment.id,
            'user_id': self.apt_manager.id,
        })
        user_summary = f'{appointment_type.name} with {host_partner.name or "somebody"}'
        for event, summary in ((appointment, user_summary), (resource_event, resource_event.name)):
            with self.subTest(summary=summary):
                self.assertEqual(event._get_customer_summary(), summary)

    @users('apt_manager')
    @freeze_time('2022-02-13T20:00:00')
    def test_generate_slots_punctual_appointment_type(self):
        """ Generates recurring slots, check begin and end slot boundaries depending on the start and end datetimes. """
        apt_type = self.env['appointment.type'].create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'punctual',
            'location_id': self.staff_user_bxls.partner_id.id,
            'name': 'Punctual Appt Type',
            'max_schedule_days': False,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'start_datetime': datetime(2022, 2, 14, 8, 0, 0),
            'end_datetime': datetime(2022, 2, 20, 20, 0, 0),
            'slot_ids': [
                (0, False, {'weekday': weekday,
                            'start_hour': hour,
                            'end_hour': hour + 1,
                           })
                for weekday in ['1', '2']
                for hour in range(8, 14)
            ],
            'staff_user_ids': [(4, self.staff_user_bxls.id)],
        }).with_user(self.env.user)

        slots_weekdays = {slot.weekday for slot in apt_type.slot_ids}
        timezone = 'Europe/Brussels'
        requested_tz = pytz.timezone(timezone)
        # reference_now: datetime(2022, 2, 13, 20, 0, 0) (sunday evening)
        # apt slot_ids: Monday 8AM -> 2PM, Tuesday 8AM -> 2PM

        cases = [
            # start datetime / end_datetime (UTC)
            (datetime(2022, 2, 14, 9, 0, 0), datetime(2022, 2, 25, 9, 0, 0)), # Slots fully in the future
            (datetime(2022, 2, 1, 9, 0, 0), datetime(2022, 2, 25, 9, 0, 0)), # start_datetime < now < end_datetimes
            (datetime(2022, 2, 1, 9, 0, 0), datetime(2022, 2, 12, 9, 0, 0)), # Slots fully in the past
        ]
        expected = [
            # first slot start datetime / last slot end_datetime (UTC)
            (datetime(2022, 2, 14, 9, 0, 0), datetime(2022, 2, 22, 13, 0, 0)), # start = specified start_datetime
            (datetime(2022, 2, 14, 7, 0, 0), datetime(2022, 2, 22, 13, 0, 0)), # start = 8AM from apt slots_ids converted to UTC
            (False, False)
        ]

        for (start_datetime, end_datetime), (first_slot_expected_start, last_slot_expected_end) in zip(cases, expected):
            with self.subTest(start_datetime=start_datetime, end_datetime=end_datetime):
                apt_type.write({'start_datetime': start_datetime, 'end_datetime': end_datetime})
                reference_date = start_datetime if start_datetime > self.reference_now else self.reference_now
                first_day = requested_tz.fromutc(reference_date)
                last_day = requested_tz.fromutc(end_datetime)
                slots = apt_type._slots_generate(first_day, last_day, timezone, reference_date=reference_date)
                if not slots:
                    self.assertFalse(first_slot_expected_start)
                    self.assertFalse(last_slot_expected_end)
                    continue
                self.assertTrue({slot['slot'].weekday for slot in slots}.issubset(slots_weekdays), 'Slots: wrong weekday')
                self.assertEqual(slots[0]['UTC'][0], first_slot_expected_start, 'Slots: wrong first slot start datetime')
                self.assertEqual(slots[-1]['UTC'][1], last_slot_expected_end, 'Slots: wrong last slot end datetime')

    @users('apt_manager')
    def test_generate_slots_recurring(self):
        """ Generates recurring slots, check begin and end slot boundaries. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_start_hour_day_overflow(self):
        """ Generates recurring slots, make sure we don't overshoot the current day and generate meaningless slots """
        slots = [{
            'weekday': '1',
            'start_hour': 9.0,
            'end_hour': 10.0,
        }, {
            'weekday': '1',
            'start_hour': 10.0,
            'end_hour': 11.0,
        }, {
            'weekday': '1',
            'start_hour': 15.0,
            'end_hour': 16.0,
        }, {
            'weekday': '2',
            'start_hour': 9.0,
            'end_hour': 17.0,
        },]
        apt_type = self.env['appointment.type'].create({
            'appointment_duration': 1.0,
            'appointment_tz': 'Europe/Brussels',
            'category': 'recurring',
            'name': 'Overflow Appointment',
            'max_schedule_days': 8,
            'min_schedule_hours': 12.0,
            'slot_ids': [(0, 0, slot) for slot in slots],
            'staff_user_ids': [self.env.user.id],
        })

        # Check around the 11AM(Brussels) mark, or 15:30PM(Kolkata)
        # If we add 12 for the minimum schedule hour it's past 11PM
        # Past 11 the appointment duration will put us past the current day
        brussels_tz = pytz.timezone('Europe/Brussels')
        for hour, minute in [[h, m] for h in [2, 9, 10, 11, 12] for m in [0, 1, 59]]:
            time = brussels_tz.localize(self.reference_monday.replace(hour=hour, minute=minute))
            with freeze_time(time):
                slots = apt_type._get_appointment_slots('Asia/Kolkata')
            self.assertSlots(
                slots,
                [{'name_formated': 'February 2022',
                  'month_date': datetime(2022, 2, 1),
                  'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
                 }
                ],
                {'enddate': date(2022, 3, 5),
                 'startdate': self.reference_now_monthweekstart,
                 'slots_day_specific': { # +4 instead of +4.5 because the test method only accounts for the absolute hour
                    time.date(): [{'start': 15 + 4, 'end': 16 + 4}] if hour == 2 else [], # min_schedule_hours is too large
                    (time + timedelta(days=1)).date(): [{'start': start + 4, 'end': start + 5} for start in range(9, 17)],
                    (time + timedelta(days=7)).date(): [{'start': start + 4, 'end': start + 5} for start in range(9, 11)] + [{'start': 15 + 4, 'end': 16 + 4}],
                    (time + timedelta(days=8)).date(): [{'start': start + 4, 'end': start + 5} for start in range(9, 17)],
                 },
                 'slots_start_hours': [],
                 'slots_startdate': time.date(),
                 'slots_weekdays_nowork': range(2, 7)
                },
            )

    @users('apt_manager')
    def test_generate_slots_recurring_UTC(self):
        """ Generates recurring slots, check begin and end slot boundaries. Force
        UTC results event if everything is Europe/Brussels based. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_start_hours': [7, 8, 9, 10, 11, 12],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('admin')
    def test_generate_slots_recurring_westrict(self):
        """ Generates recurring slots, check user restrictions """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)
        # add second staff user and split days based on the two people
        apt_type.write({'staff_user_ids': [(4, self.staff_user_aust.id)]})
        apt_type.slot_ids.filtered(lambda slot: slot.weekday == '1').write({
            'restrict_to_user_ids': [(4, self.staff_user_bxls.id)],
        })
        apt_type.slot_ids.filtered(lambda slot: slot.weekday != '1').write({
            'restrict_to_user_ids': [(4, self.staff_user_aust.id)],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

        # check staff_user_id
        monday_slots = [
            slot
            for month in slots for week in month['weeks'] for day in week
            for slot in day['slots']
            if day['day'].weekday() == 0
        ]
        tuesday_slots = [
            slot
            for month in slots for week in month['weeks'] for day in week
            for slot in day['slots']
            if day['day'].weekday() == 1
        ]
        self.assertEqual(len(monday_slots), 18, 'Slots: 3 mondays of 6 slots')
        self.assertTrue(all(slot['staff_user_id'] == self.staff_user_bxls.id for slot in monday_slots))
        self.assertEqual(len(tuesday_slots), 12, 'Slots: 2 tuesdays of 6 slots (3rd tuesday is out of range')
        self.assertTrue(all(slot['staff_user_id'] == self.staff_user_aust.id for slot in tuesday_slots))

    @users('apt_manager')
    def test_generate_slots_recurring_wmeetings(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create meetings
        _meetings = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 3 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=3),
              False
             ),
             (self.reference_monday + timedelta(days=7), # next Monday: one full day
              self.reference_monday + timedelta(days=7, hours=1),
              True,
             ),
             (self.reference_monday + timedelta(days=8, hours=2), # 1 hour next Tuesday (9 UTC)
              self.reference_monday + timedelta(days=8, hours=3),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=3), # 1 hour next Tuesday (10 UTC, declined)
              self.reference_monday + timedelta(days=8, hours=4),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=5), # 2 hours next Tuesday (12 UTC)
              self.reference_monday + timedelta(days=8, hours=7),
              False,
             ),
            ]
        )
        attendee = _meetings[-2].attendee_ids.filtered(lambda att: att.partner_id == self.staff_user_bxls.partner_id)
        attendee.do_decline()

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_day_specific': {
                (self.reference_monday + timedelta(days=1)).date(): [
                    {'end': 12, 'start': 11},
                    {'end': 13, 'start': 12},
                    {'end': 14, 'start': 13},
                ],  # meetings on 7-10 UTC
                (self.reference_monday + timedelta(days=7)).date(): [],  # on meeting "allday"
                (self.reference_monday + timedelta(days=8)).date(): [
                    {'end': 9, 'start': 8},
                    {'end': 10, 'start': 9},
                    {'end': 12, 'start': 11},
                    {'end': 13, 'start': 12},
                ],  # meetings 9-10 and 12-14
             },
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_unique(self):
        """ Check unique slots (note: custom appointment type does not check working
        hours). """
        unique_slots = [{
            'start_datetime': self.reference_monday.replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(hours=1)).replace(microsecond=0),
            'allday': False,
        }, {
            'start_datetime': (self.reference_monday + timedelta(days=1)).replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(days=2)).replace(microsecond=0),
            'allday': True,
        }]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(5, 0)] + [
                (0, 0, {'allday': slot['allday'],
                        'end_datetime': slot['end_datetime'],
                        'slot_type': 'unique',
                        'start_datetime': slot['start_datetime'],
                       }
                ) for slot in unique_slots
            ],
        })
        self.assertEqual(apt_type.category, 'custom', "It should be a custom appointment type")
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)
        self.assertEqual(len(apt_type.slot_ids), 2, "Two slots should have been assigned to the appointment type")

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_day_specific': {
                self.reference_monday.date(): [{'end': 9, 'start': 8}],  # first unique 1 hour long
                (self.reference_monday + timedelta(days=1)).date(): [{'allday': True, 'end': False, 'start': 8}],  # second unique all day-based
             },
             'slots_start_hours': [],  # all slots in this tests are unique, other dates have no slots
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_multi_user_slot_availabilities(self):
        """ Check that when called with no user / one user / several users, the methods computing the slots work as expected:
        if no user is set, all users of the appointment_type will be used. If one or more users are set, they will be used to
        compute availabilities. If users given as argument is not among the staff of the appointment type, return empty list.
        This test only concern random appointments: if it were 'chosen' assignment, then the dropdown of user selection would
        be in the view. Hence, in practice, only one user would be used to generate / update the slots : the one selected. For
        random ones, the users can be multiple if a filter is set, assigning randomly among several users. This tests asserts
        that _get_appointment_slots returns slots properly when called with several users too. If no filter, then the update
        method would be called with staff_users = False (since select not in view, getting the input value returns false) """
        reference_monday = self.reference_monday.replace(microsecond=0)
        reccuring_slots_utc = [{
            'weekday': '1',
            'start_hour': 6.0,  # 1 slot : Monday 06:00 -> 07:00
            'end_hour': 7.0,
        }, {
            'weekday': '2',
            'start_hour': 9.0,  # 2 slots : Tuesday 09:00 -> 11:00
            'end_hour': 11.0,
        }]
        staff_user_no_tz = mail_new_test_user(
            self.env(su=True),
            company_id=self.company_admin.id,
            email='no_tz@test.example.com',
            groups='base.group_user',
            name='Employee Without Tz',
            notification_type='email',
            login='staff_user_no_tz',
            tz=False,
        )
        apt_type_UTC = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'max_schedule_days': 5,  # Only consider the first three slots
            'name': 'Private Guitar Lesson',
            'slot_ids': [(0, False, {
                'weekday': slot['weekday'],
                'start_hour': slot['start_hour'],
                'end_hour': slot['end_hour'],
            }) for slot in reccuring_slots_utc],
            'staff_user_ids': [self.staff_user_aust.id, self.staff_user_bxls.id, staff_user_no_tz.id],
        })

        exterior_staff_user = self.apt_manager
        # staff_user_bxls is only available on Wed and staff_user_aust only on Mon and Tue
        self._create_meetings(
            self.staff_user_bxls,
            [(reference_monday - timedelta(hours=1),  # Monday 06:00 -> 07:00
              reference_monday,
              False
              )]
        )
        self._create_meetings(
            self.staff_user_aust,
            [(reference_monday + timedelta(days=1, hours=2),  # Tuesday 09:00 -> 11:00
              reference_monday + timedelta(days=1, hours=4),
              False
              )]
        )
        # staff_user_no_tz is only available on Tue between 10 and 11 AM
        self._create_meetings(
            staff_user_no_tz,
            [(
                self.reference_monday,
                self.reference_monday.replace(hour=9),
                True
            ), (
                self.reference_monday + timedelta(days=1, hours=2),
                self.reference_monday + timedelta(days=1, hours=3),
                False
            )])

        with freeze_time(self.reference_now):
            slots_no_user = apt_type_UTC._get_appointment_slots('UTC')
            slots_exterior_user = apt_type_UTC._get_appointment_slots('UTC', exterior_staff_user)
            slots_user_aust = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_aust)
            slots_user_all = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_bxls | self.staff_user_aust)
            slots_user_bxls_exterior_user = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_bxls | exterior_staff_user)
            slots_user_no_tz = apt_type_UTC._get_appointment_slots('UTC', staff_user_no_tz)

        self.assertTrue(len(self._filter_appointment_slots(slots_no_user)) == 3)
        self.assertFalse(slots_exterior_user)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_aust)) == 1)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_all)) == 3)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_bxls_exterior_user)) == 2)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_no_tz)) == 1)

    @users('apt_manager', 'staff_user_bxls')
    def test_partner_on_leave_with_conflicting_event(self):
        """Check that conflicting meetings are correctly reflected in the on_leave_partner_ids field.

        Overlapping times between any other meeting of the employee and the meeting should add the partner
        to the list of unavailable partners.
        """
        self.env['calendar.event'].search([('user_id', '=', self.staff_user_bxls.id)]).unlink()
        self.env['resource.calendar.leaves'].sudo().search([('calendar_id', '=', self.staff_user_bxls.resource_calendar_id.id)]).unlink()
        [meeting] = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday,
              self.reference_monday + timedelta(hours=3),
              False,
              )],
            self.apt_type_bxls_2days.id
        )
        self.assertFalse(meeting.on_leave_partner_ids)
        [conflicting_meeting] = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday,
              self.reference_monday + timedelta(minutes=5),
              False,
              )],
        )
        meeting.invalidate_recordset()
        self.assertEqual(meeting.on_leave_partner_ids, self.staff_user_bxls.partner_id)
        self.assertFalse(conflicting_meeting.on_leave_partner_ids)

    @users('apt_manager')
    def test_slots_for_today(self):
        test_reference_now = datetime(2022, 2, 14, 11, 0, 0)  # is a Monday
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'min_schedule_hours': 1.0,
            'max_schedule_days': 8,
            'name': 'Test',
            'slot_ids': [(0, 0, {
                'weekday': str(test_reference_now.isoweekday()),
                'start_hour': 6,
                'end_hour': 18,
            })],
            'staff_user_ids': [self.staff_user_bxls.id],
        })
        first_day = (test_reference_now + timedelta(hours=appointment.min_schedule_hours)).astimezone(pytz.UTC)
        last_day = (test_reference_now + timedelta(days=appointment.max_schedule_days)).astimezone(pytz.UTC)
        with freeze_time(test_reference_now):
            slots = appointment._slots_generate(first_day, last_day, 'UTC')

        self.assertEqual(len(slots), 18, '2 mondays of 12 slots but 6 would be before reference date')
        for slot in slots:
            self.assertTrue(
                test_reference_now.astimezone(pytz.UTC) < slot['UTC'][0].astimezone(pytz.UTC),
                "A slot shouldn't be generated before the first_day datetime")

    @users('apt_manager')
    def test_slots_days_min_schedule(self):
        """ Test that slots are generated correctly when min_schedule_hours is 47.0.
        This means that the first returned slots should be on wednesday at 11:36.
        """
        test_reference_now = datetime(2022, 2, 14, 11, 45, 0)  # is a Monday
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'appointment_duration': 1.2,  # 1h12
            'min_schedule_hours': 47.0,
            'max_schedule_days': 8,
            'name': 'Test',
            'slot_ids': [
                (0, False, {'weekday': weekday,
                            'start_hour': 8,
                            'end_hour': 14,
                            })
                for weekday in map(str, range(1, 4))
            ],
            'staff_user_ids': [self.staff_user_bxls.id],
        })
        first_day = (test_reference_now + timedelta(hours=appointment.min_schedule_hours)).astimezone(pytz.UTC)
        last_day = (test_reference_now + timedelta(days=appointment.max_schedule_days)).astimezone(pytz.UTC)
        with freeze_time(test_reference_now):
            slots = appointment._slots_generate(first_day, last_day, 'UTC')

        for slot in slots:
            self.assertTrue(
                first_day < slot['UTC'][0].astimezone(pytz.UTC),
                "A slot shouldn't be generated before the first_day datetime")
        self.assertEqual(len(slots), 12)  # 2 days of 5 slots and 2 slots on wednesday

    @users('apt_manager')
    def test_slots_days_min_schedule_punctual(self):
        """ Test that slots are generated correctly when min_schedule_hours is 47.0 for punctual appointment.
        This means that the first returned slots should be on wednesday at 11:36.
        """
        test_reference_now = datetime(2022, 2, 14, 11, 45, 0)  # is a Monday
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'appointment_duration': 1.2,  # 1h12
            'category': 'punctual',
            'min_schedule_hours': 47.0,
            'max_schedule_days': False,
            'name': 'Test',
            'slot_ids': [
                (0, False, {'weekday': weekday,
                            'start_hour': 8,
                            'end_hour': 14,
                           })
                for weekday in ['1', '2', '3', '4', '5']
            ],
            'start_datetime': datetime(2022, 2, 15, 9, 0, 0),
            'end_datetime': datetime(2022, 2, 25, 9, 0, 0),
            'staff_user_ids': [self.staff_user_bxls.id],
        })
        with freeze_time(test_reference_now):
            slots = appointment.sudo()._get_appointment_slots('UTC')
        slots = self._filter_appointment_slots(slots)
        self.assertEqual(slots[0]['datetime'], "2022-02-16 11:36:00",
                         "The first slot should take into account the min schedule hours")
        self.assertEqual(slots[-1]['datetime'], "2022-02-24 12:48:00")

    @users('staff_user_aust')
    def test_timezone_delta(self):
        """ Test timezone delta. Not sure what original test was really doing. """
        # As if the second user called the function
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user).with_context(
            lang='en_US',
            tz=self.staff_user_aust.tz,
            uid=self.staff_user_aust.id,
        )

        # Do what the controller actually does, aka sudo
        with freeze_time(self.reference_now):
            slots = apt_type.sudo()._get_appointment_slots('Australia/Perth', filter_users=None)

        global_slots_enddate = date(2022, 4, 2)  # last day of last week of March
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'month_date': datetime(2022, 3, 1),
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_enddate': self.reference_now.date() + timedelta(days=15),  # maximum 2 weeks of slots
             'slots_start_hours': [15, 16, 17, 18, 19, 20],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves, set in UTC+8
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_unique_slots_availabilities(self):
        """ Check that the availability of each unique slot is correct.
        First we test that the 2 unique slots of the custom appointment type
        are available. Then we check that there is now only 1 availability left
        after the creation of a meeting which encompasses a slot. """
        reference_monday = self.reference_monday.replace(microsecond=0)
        unique_slots = [{
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=1),
            'start_datetime': reference_monday,
        }, {
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=3),
            'start_datetime': reference_monday + timedelta(hours=2),
        }]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(0, 0, {
                'allday': slot['allday'],
                'end_datetime': slot['end_datetime'],
                'slot_type': 'unique',
                'start_datetime': slot['start_datetime'],
                }) for slot in unique_slots
            ],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        # get all monday slots where apt_manager is available
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_users=self.apt_manager)
        self.assertEqual(len(available_unique_slots), 2)

        # Create a meeting encompassing the first unique slot
        self._create_meetings(self.apt_manager, [(
            unique_slots[0]['start_datetime'],
            unique_slots[0]['end_datetime'],
            False,
        )])

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_users=self.apt_manager)
        self.assertEqual(len(available_unique_slots), 1)
        self.assertEqual(
            available_unique_slots[0]['datetime'],
            unique_slots[1]['start_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        )

    @users('apt_manager')
    def test_synchronize_restricted_resource_and_staff_to_appointment_type(self):
        """ Check that when changing staff users or resources, the appointment slots adapt their
            restricted users/resources to only keep the new staff users / resources. Remove the rest.
            When changing schedule_based_on, remove previous mode users/ resources on both type and slots.
        """
        appointment_type = self.apt_type_bxls_2days
        self.assertTrue(len(appointment_type.slot_ids) >= 3)
        slot_1, slot_2, slot_3 = appointment_type.slot_ids[:3]

        appointment_type.staff_user_ids = [(6, False, [self.apt_manager.id, self.staff_user_bxls.id])]
        self.assertEqual(appointment_type.staff_user_ids, self.apt_manager | self.staff_user_bxls)
        slot_1.restrict_to_user_ids = [self.apt_manager.id, self.staff_user_bxls.id]
        slot_2.restrict_to_user_ids = [self.apt_manager.id]
        slot_3.restrict_to_user_ids = []
        self.assertEqual(slot_1.restrict_to_user_ids, self.apt_manager | self.staff_user_bxls)
        self.assertEqual(slot_2.restrict_to_user_ids, self.apt_manager)
        self.assertFalse(slot_3.restrict_to_user_ids)

        appointment_type.staff_user_ids = [(6, False, [self.staff_user_bxls.id, self.staff_user_aust.id])]
        self.assertEqual(appointment_type.staff_user_ids, self.staff_user_bxls | self.staff_user_aust)
        self.assertEqual(slot_1.restrict_to_user_ids, self.staff_user_bxls)
        self.assertFalse(slot_2.restrict_to_user_ids)
        self.assertFalse(slot_3.restrict_to_user_ids)

        appointment_type.schedule_based_on = 'resources'
        self.assertFalse(appointment_type.staff_user_ids)
        self.assertFalse(slot_1.restrict_to_user_ids | slot_2.restrict_to_user_ids | slot_3.restrict_to_user_ids)
        resource_1, resource_2, resource_3 = self.env['appointment.resource'].create([{
            'appointment_type_ids': appointment_type.ids,
            'name': 'Resource 1',
        }, {
            'appointment_type_ids': appointment_type.ids,
            'name': 'Resource 2',
        }, {
            'appointment_type_ids': appointment_type.ids,
            'name': 'Resource 3',
        }])

        self.assertEqual(appointment_type.resource_ids, resource_1 | resource_2 | resource_3)
        slot_1.restrict_to_resource_ids = [resource_1.id, resource_2.id]
        slot_2.restrict_to_resource_ids = [resource_1.id]
        slot_3.restrict_to_resource_ids = []
        self.assertEqual(slot_1.restrict_to_resource_ids, resource_1 | resource_2)
        self.assertEqual(slot_2.restrict_to_resource_ids, resource_1)
        self.assertFalse(slot_3.restrict_to_user_ids)

        appointment_type.resource_ids = [(6, False, [resource_2.id, resource_3.id])]
        self.assertEqual(appointment_type.resource_ids, resource_2 | resource_3)
        self.assertEqual(slot_1.restrict_to_resource_ids, resource_2)
        self.assertFalse(slot_2.restrict_to_resource_ids)
        self.assertFalse(slot_3.restrict_to_resource_ids)

        appointment_type.schedule_based_on = 'users'
        self.assertFalse(appointment_type.resource_ids)
        self.assertFalse(slot_1.restrict_to_resource_ids | slot_2.restrict_to_resource_ids | slot_3.restrict_to_resource_ids)

    def test_check_appointment_timezone(self):
        session = self.authenticate(None, None)
        odoo.http.root.session_store.save(session)
        appointment = self.apt_type_bxls_2days
        appointment_invite = self.env['appointment.invite'].create({'appointment_type_ids': appointment.ids})
        appointment_url = url_join(appointment.get_base_url(), '/appointment/%s' % appointment.id)
        appointment_info_url = "%s/info?" % appointment_url
        url_inside_of_slot = appointment_info_url + url_encode({
            'staff_user_id': self.staff_user_bxls.id,
            'date_time': datetime(2023, 1, 9, 9, 0),  # 9/01/2023 is a Monday, there is a slot at 9:00
            'duration': 1,
            **appointment_invite._get_redirect_url_parameters(),
        })
        # User should be able open url without timezone session
        self.url_open(url_inside_of_slot)

    @freeze_time('2022-02-14')
    @users('apt_manager')
    def test_different_timezones_with_allday_events_availabilities(self):
        """
        When the utc offset of the timezone is large, it is possible that the day of the week no longer corresponds.
        Testing that allday event slots are all not available.
        """
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'Pacific/Auckland',
            'appointment_duration': 21,
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'location_id': self.staff_user_nz.partner_id.id,
            'name': 'New Zealand Appointment',
            'max_schedule_days': 14,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'slot_ids': [(0, 0, {
                'weekday': '1',
                'start_hour': 1,
                'end_hour': 23,
            })],
            'staff_user_ids': [(4, self.staff_user_nz.id)],
        })
        self._create_meetings(
            self.staff_user_nz,
            [(self.reference_monday + timedelta(days=7),
              self.reference_monday + timedelta(days=7, hours=1),
              True
              )])
        slots = appointment._get_appointment_slots(
            appointment.appointment_tz)
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': date(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
              }
             ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
             'slots_start_hours': [],
             # first Monday after reference_now
             'slots_startdate': self.reference_monday.date() + timedelta(days=7),
             # only test that day
             'slots_enddate': self.reference_monday.date() + timedelta(days=14),
             'slots_day_specific': {date(2022, 2, 28): [{'start':1}]}
             }
        )

    def test_no_activity_creation_on_apt_booking(self):
        """ Test that no activity is created on appointment booking. """
        apt_type = self.apt_type_bxls_2days
        self.env['calendar.event'].with_user(self.apt_manager).with_context(
            default_res_model=apt_type._name,
            default_res_id=apt_type.id,
        ).create({
            'name': 'Appointment Meeting',
            'start': datetime(2022, 2, 1, 10, 0, 0),
            'stop': datetime(2022, 2, 1, 11, 0, 0),
            'appointment_type_id': apt_type.id,
        })
        self.assertEqual(len(apt_type.activity_ids), 0)
        # Ensure that activities are created if model is not appointment.type
        test_record = self.env['res.partner'].create({
            'name': 'User 0',
        })
        self.env['calendar.event'].with_user(self.user_demo).with_context(
            default_res_model=test_record._name,
            default_res_id=test_record.id,
        ).create({
            'name': 'Normal Meeting',
            'start': datetime(2022, 2, 1, 11, 0, 0),
            'stop': datetime(2022, 2, 1, 12, 0, 0),
        })
        self.assertEqual(len(test_record.activity_ids), 1)
