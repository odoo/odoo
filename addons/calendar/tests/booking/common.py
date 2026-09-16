from contextlib import contextmanager
from datetime import UTC, date, datetime
from unittest.mock import patch

from odoo.tests import common, tagged

from odoo.addons.calendar.models.calendar_event import CalendarEvent
from odoo.addons.calendar.models.res_partner import ResPartner
from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.addons.resource.models.resource_calendar import ResourceCalendar


class AppointmentCommon(MailCase, common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ensure admin configuration
        cls.admin_user = cls.env.ref("base.user_admin")
        cls.admin_user.write(
            {
                "country_id": cls.env.ref("base.be").id,
                "login": "admin",
                "notification_type": "inbox",
                "tz": "Europe/Brussels",
            }
        )
        cls.company_admin = cls.admin_user.company_id
        # set country in order to format Belgian numbers
        cls.company_admin.write(
            {
                "country_id": cls.env.ref("base.be").id,
            }
        )

        # reference dates to have reproducible tests (sunday evening, allowing full week)
        cls.reference_now = datetime(2022, 2, 13, 20, 0, 0)
        cls.reference_monday = datetime(2022, 2, 14, 7, 0, 0)
        cls.reference_now_monthweekstart = date(
            2022, 1, 30
        )  # starts on a Sunday, first week containing Feb day
        cls.global_slots_enddate = date(2022, 3, 5)  # last day of last week of February

        cls.apt_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="apt_manager@test.example.com",
            groups="base.group_user,calendar.group_appointment_manager",
            name="Appointment Manager",
            notification_type="email",
            login="apt_manager",
            tz="Europe/Brussels",
        )
        cls.apt_user = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="apt_user@test.example.com",
            groups="base.group_user,calendar.group_appointment_user",
            name="Appointment User",
            notification_type="email",
            login="apt_user",
            tz="Europe/Brussels",
        )
        cls.staff_user_bxls = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="brussels@test.example.com",
            groups="base.group_user",
            name="Employee Brussels",
            notification_type="email",
            login="staff_user_bxls",
            tz="Europe/Brussels",  # UTC + 1 (at least in February)
        )
        cls.staff_user_aust = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="australia@test.example.com",
            groups="base.group_user",
            name="Employee Australian",
            notification_type="email",
            login="staff_user_aust",
            tz="Australia/Perth",  # UTC + 8 (at least in February)
        )
        cls.staff_user_nz = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="new_zealand@test.example.com",
            groups="base.group_user",
            name="Employee New Zealand",
            notification_type="email",
            login="staff_user_nz",
            tz="Pacific/Auckland",  # UTC + 12
        )
        cls.staff_users = cls.staff_user_bxls + cls.staff_user_aust + cls.staff_user_nz

        # Default (test) appointment type
        # Slots are each hours from 8 to 13 (UTC + 1)
        # -> working hours: 7, 8, 9, 10 and 12 UTC as 11 is lunch time in working hours
        cls.apt_type_bxls_2days = cls.env["appointment.type"].create(
            {
                "appointment_tz": "Europe/Brussels",
                "appointment_duration": 1,
                "is_auto_assign": True,
                "category": "recurring",
                "location_id": cls.staff_user_bxls.partner_id.id,
                "name": "Bxls Appt Type",
                "max_schedule_days": 15,
                "min_cancellation_hours": 1,
                "min_schedule_hours": 1,
                "slot_ids": [
                    (
                        0,
                        False,
                        {
                            "weekday": weekday,
                            "start_hour": hour,
                            "end_hour": hour + 1,
                        },
                    )
                    for weekday in ["1", "2"]
                    for hour in range(8, 14)
                ],
                "staff_user_ids": [(4, cls.staff_user_bxls.id)],
            }
        )

        cls.apt_type_manage_capacity_users = cls.env["appointment.type"].create(
            {
                "appointment_tz": "Europe/Brussels",
                "appointment_duration": 1,
                "is_auto_assign": False,
                "is_date_first": True,
                "category": "recurring",
                "location_id": cls.staff_user_bxls.partner_id.id,
                "name": "Bxls Appt Type with capacity",
                "max_schedule_days": 15,
                "min_cancellation_hours": 1,
                "schedule_based_on": "users",
                "manage_capacity": True,
                "min_schedule_hours": 1,
                "staff_user_ids": [
                    (6, 0, [cls.staff_user_aust.id, cls.staff_user_bxls.id])
                ],
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(cls.reference_monday.isoweekday()),
                            "start_hour": 15,
                            "end_hour": 16,
                        },
                    )
                ],
                "user_capacity": 5,
            }
        )

        cls.apt_type_resource = cls.env["appointment.type"].create(
            {
                "appointment_tz": "UTC",
                "is_auto_assign": True,
                "min_schedule_hours": 1.0,
                "max_schedule_days": 5,
                "name": "Test",
                "manage_capacity": True,
                "schedule_based_on": "resources",
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(cls.reference_monday.isoweekday()),
                            "start_hour": 15,
                            "end_hour": 16,
                        },
                    )
                ],
            }
        )

        cls.apt_user_multiple_bookings, cls.apt_resource_multiple_bookings = cls.env[
            "appointment.type"
        ].create(
            [
                {
                    "appointment_tz": "Europe/Brussels",
                    "appointment_duration": 1,
                    "is_auto_assign": True,
                    "max_schedule_days": 15,
                    "min_cancellation_hours": 1,
                    "min_schedule_hours": 1,
                    "max_bookings": 3,
                    "name": "Bxls Users Appt Type with multiple bookings",
                    "slot_ids": [
                        (
                            0,
                            False,
                            {
                                "weekday": weekday,
                                "start_hour": hour,
                                "end_hour": hour + 1,
                            },
                        )
                        for weekday in ["1", "2"]
                        for hour in range(8, 14)
                    ],
                    "staff_user_ids": [
                        (6, 0, [cls.staff_user_aust.id, cls.staff_user_bxls.id])
                    ],
                },
                {
                    "appointment_tz": "Europe/Brussels",
                    "appointment_duration": 1,
                    "is_auto_assign": True,
                    "max_bookings": 3,
                    "max_schedule_days": 15,
                    "min_cancellation_hours": 1,
                    "min_schedule_hours": 1,
                    "name": "Bxls Resource Appt Type with multiple bookings",
                    "schedule_based_on": "resources",
                    "slot_ids": [
                        (
                            0,
                            False,
                            {
                                "weekday": weekday,
                                "start_hour": hour,
                                "end_hour": hour + 1,
                            },
                        )
                        for weekday in ["1", "2"]
                        for hour in range(8, 14)
                    ],
                },
            ]
        )

    def _test_url_open(self, url):
        """Call url_open with nocache parameter"""
        url += (("?" not in url and "?") or "&") + "nocache"
        return self.url_open(url)

    def _create_meetings(
        self, user, time_info, appointment_type_id=None, show_as="busy"
    ):
        return (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                [
                    {
                        "allday": allday,
                        "attendee_ids": [(0, 0, {"partner_id": user.partner_id.id})],
                        "name": "Event for %s (%s / %s - %s)"
                        % (user.name, allday, start, stop),
                        "partner_ids": [(4, user.partner_id.id)],
                        "start": start,
                        "stop": stop,
                        "user_id": user.id,
                        "appointment_type_id": appointment_type_id,
                        "show_as": show_as,
                    }
                    for start, stop, allday in time_info
                ]
            )
        )

    def _create_invite_test_data(self):
        apt_type_test = self.env["appointment.type"].create(
            {
                "name": "Appointment Test",
            }
        )
        self.all_apts = self.apt_type_bxls_2days + apt_type_test
        self.invite_apt_type_bxls_2days = self.env["appointment.invite"].create(
            {
                "appointment_type_ids": self.apt_type_bxls_2days.ids,
            }
        )
        self.invite_all_apts = self.env["appointment.invite"].create(
            {
                "appointment_type_ids": self.all_apts.ids,
            }
        )

    def _filter_appointment_slots(
        self,
        slots,
        filter_months=False,
        filter_weekdays=False,
        filter_users=False,
        filter_resources=False,
    ):
        """Flatten computed slots into slot dicts, optionally restricted to some months,
        weekdays, users or resources.

        :param list slots: slots content computed from _get_appointment_slots()
        :param list filter_months: months to keep as (month, year) tuples, e.g. [(2, 2022)]
            for February 2022
        :param list filter_weekdays: weekdays to keep as integers, 0 = monday and 6 = sunday,
            e.g. [0, 1, 3] to keep only monday, tuesday and thursday slots
        :param recordset filter_users: users for which slots are kept when they are available
        :param recordset filter_resources: resources for which slots are kept when all the
            slot available resources belong to them
        :return: matching slots, e.g. [{
            'datetime': '2022-02-14 08:00:00',
            'duration': '1.0',
            'staff_user_id': 21,
            'hours': '08:00 - 09:00',
        }, ...]
        :rtype: list
        """
        slots_info = []
        for month in slots:
            # We use the last day of the first week to be sure that we use the correct month
            last_day_first_week = month["weeks"][0][-1]["day"]
            month_tuple = (last_day_first_week.month, last_day_first_week.year)
            if filter_months and month_tuple not in filter_months:
                continue
            for week in month["weeks"]:
                for day in week:
                    if not day["slots"] or (
                        filter_weekdays and day["day"].weekday() not in filter_weekdays
                    ):
                        continue
                    for slot in day["slots"]:
                        if (
                            filter_users
                            and slot.get("staff_user_id") not in filter_users.ids
                        ):
                            continue
                        if filter_resources:
                            if any(
                                slot_resource["id"] not in filter_resources.ids
                                for slot_resource in slot.get("available_resources")
                            ):
                                continue
                        slots_info.append(slot)
        return slots_info

    def assertSlots(self, slots, exp_months, slots_data):
        """Check slots content, currently doing only basic checks."""
        self.assertEqual(
            len(slots), len(exp_months), "Slots: wrong number of covered months"
        )
        self.assertEqual(
            slots[0]["weeks"][0][0]["day"],
            slots_data["startdate"],
            "Slots: wrong starting date",
        )
        self.assertEqual(
            slots[-1]["weeks"][-1][-1]["day"],
            slots_data["enddate"],
            "Slots: wrong ending date",
        )
        for month, expected_month in zip(slots, exp_months, strict=False):
            self.assertEqual(month["month"], expected_month["name_formated"])
            self.assertEqual(len(month["weeks"]), expected_month["weeks_count"])
            if not slots_data.get("slots_startdate"):  # not all tests are detailed
                continue

            # global slots configuration
            slots_days_leave = slots_data.get("slots_days_leave", [])
            slots_enddate = slots_data.get("slots_enddate")
            slots_startdate = slots_data.get("slots_startdate")
            slots_weekdays_nowork = slots_data.get("slots_weekdays_nowork", [])

            # slots specific
            slots_start_hours = slots_data.get("slots_start_hours", [])

            for week in month["weeks"]:
                for day in week:
                    day_date = day["day"]
                    # days linked to "next month" or "previous month" are there for filling but have no slots
                    is_void = day_date.month != expected_month["month_date"].month

                    # before reference date: no slots generated (just there to fill up calendar)
                    is_working = day_date >= slots_startdate
                    if is_working and slots_enddate:
                        is_working = day_date <= slots_enddate
                    if is_working:
                        is_working = day_date not in slots_days_leave
                    if is_working:
                        is_working = day_date.weekday() not in slots_weekdays_nowork
                    # after end date: no slots generated (just there to fill up calendar)

                    # standard day: should have slots according to apt type slots hours
                    if not is_void and is_working:
                        if day_date in slots_data.get("slots_day_specific", {}):
                            slot_count = len(slots_data["slots_day_specific"][day_date])
                            slot_start_hours = [
                                slot["start"]
                                for slot in slots_data["slots_day_specific"][day_date]
                            ]
                        else:
                            slot_count = len(slots_start_hours)
                            slot_start_hours = slots_start_hours
                        self.assertEqual(
                            len(day["slots"]),
                            slot_count,
                            "Slot: wrong number of slots for %s" % day,
                        )
                        self.assertEqual(
                            [
                                datetime.strptime(
                                    slot["datetime"], "%Y-%m-%d %H:%M:%S"
                                ).hour
                                for slot in day["slots"]
                            ],
                            slot_start_hours,
                            "Slot: wrong starting hours",
                        )
                    elif is_void:
                        self.assertFalse(
                            len(day["slots"]),
                            "Slot: out of range should have no slot for %s" % day,
                        )
                    else:
                        self.assertFalse(
                            len(day["slots"]),
                            "Slot: not worked should have no slot for %s" % day,
                        )

    def _test_slot_generate_available_resources(
        self,
        appointment_type,
        asked_capacity,
        timezone,
        start_dt,
        end_dt,
        filter_resources,
        expected_available_resource_ids,
        reference_date=None,
    ):
        """Simulate the check done after selecting a particular time slot.

        :param recordset appointment_type: appointment type tested
        :param int asked_capacity: asked capacity for the appointment
        :param str timezone: timezone selected
        :param datetime start_dt: start datetime of the slot (naive UTC)
        :param datetime end_dt: end datetime of the slot (naive UTC)
        :param recordset filter_resources: the resources the appointment was booked for
        :param list expected_available_resource_ids: resource ids expected to be available
            for the checked slot
        :param datetime reference_date: starting datetime to fetch slots (naive UTC),
            defaults to now
        """
        slots = appointment_type._slots_generate(
            start_dt.astimezone(UTC),
            end_dt.astimezone(UTC),
            timezone,
            reference_date=reference_date,
        )
        slots = [
            slot
            for slot in slots
            if slot["UTC"]
            == (start_dt.replace(tzinfo=None), end_dt.replace(tzinfo=None))
        ]
        appointment_type._slots_add_resources_availability(
            slots,
            start_dt,
            end_dt,
            filter_resources=filter_resources,
            asked_capacity=asked_capacity,
        )
        self.assertEqual(
            set(expected_available_resource_ids),
            set(slots[0]["available_resource_ids"].ids),
        )

    @contextmanager
    def mockAppointmentCalls(self):
        _original_search = CalendarEvent.search
        _original_search_count = CalendarEvent.search_count
        _original__is_calendar_available = ResPartner._is_calendar_available
        _original_work_intervals_batch = ResourceCalendar._work_intervals_batch
        with (
            patch.object(
                CalendarEvent, "search", autospec=True, side_effect=_original_search
            ) as mock_ce_search,
            patch.object(
                CalendarEvent,
                "search_count",
                autospec=True,
                side_effect=_original_search_count,
            ) as mock_ce_sc,
            patch.object(
                ResPartner,
                "_is_calendar_available",
                autospec=True,
                side_effect=_original__is_calendar_available,
            ) as mock_partner_cal,
            patch.object(
                ResourceCalendar,
                "_work_intervals_batch",
                autospec=True,
                side_effect=_original_work_intervals_batch,
            ) as mock_cal_wit,
        ):
            self._mock_calevent_search = mock_ce_search
            self._mock_calevent_search_count = mock_ce_sc
            self._mock_partner_calendar_check = mock_partner_cal
            self._mock_cal_work_intervals = mock_cal_wit
            yield


@tagged("security")
class AppointmentSecurityCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = mail_new_test_user(
            cls.env, login="internal_user", tz="UTC", groups="base.group_user"
        )
        cls.public_user = mail_new_test_user(
            cls.env, login="public_user", tz="UTC", groups="base.group_public"
        )
        cls.common_slot_config = {
            "weekday": "1",
            "start_hour": 5,
            "end_hour": 6,
        }
        slots_configuration = [
            (
                0,
                False,
                {
                    "weekday": weekday,
                    "start_hour": hour,
                    "end_hour": hour + 1,
                },
            )
            for weekday in ["1", "2"]
            for hour in range(8, 14)
        ]
        (
            cls.apt_type_apt_manager,
            cls.apt_type_apt_user,
            cls.apt_type_internal_user,
            cls.apt_type_no_staff,
        ) = cls.env["appointment.type"].create(
            [
                {
                    "appointment_tz": "UTC",
                    "name": "Appointment with Manager as staff",
                    "slot_ids": slots_configuration,
                    "staff_user_ids": [(4, cls.apt_manager.id)],
                },
                {
                    "appointment_tz": "UTC",
                    "name": "Appointment with User as staff",
                    "slot_ids": slots_configuration,
                    "staff_user_ids": [(4, cls.apt_user.id)],
                },
                {
                    "appointment_tz": "UTC",
                    "name": "Appointment with Internal as staff",
                    "slot_ids": slots_configuration,
                    "staff_user_ids": [(4, cls.internal_user.id)],
                },
                {
                    "appointment_tz": "UTC",
                    "name": "Appointment without staff",
                    "slot_ids": slots_configuration,
                    "staff_user_ids": False,
                },
            ]
        )
        (
            cls.share_link_apt_manager,
            cls.share_link_apt_user,
            cls.share_link_internal_user,
        ) = cls.env["appointment.invite"].create(
            [
                {
                    "appointment_type_ids": cls.apt_type_apt_manager,
                    "resources_choice": "specific_resources",
                    "staff_user_ids": [(4, cls.apt_manager.id)],
                },
                {
                    "appointment_type_ids": cls.apt_type_apt_user,
                    "resources_choice": "specific_resources",
                    "staff_user_ids": [(4, cls.apt_user.id)],
                },
                {
                    "appointment_type_ids": cls.apt_type_internal_user,
                    "resources_choice": "specific_resources",
                    "staff_user_ids": [(4, cls.internal_user.id)],
                },
            ]
        )
