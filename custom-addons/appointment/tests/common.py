# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import patch

from odoo.addons.appointment.models.res_partner import Partner
from odoo.addons.calendar.models.calendar_event import Meeting
from odoo.addons.resource.models.resource_calendar import ResourceCalendar
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.tests import common


class AppointmentCommon(MailCommon, common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super(AppointmentCommon, cls).setUpClass()
        # ensure admin configuration
        cls.admin_user = cls.env.ref('base.user_admin')
        cls.admin_user.write({
            'country_id': cls.env.ref('base.be').id,
            'login': 'admin',
            'notification_type': 'inbox',
            'tz': "Europe/Brussels",
        })
        cls.company_admin = cls.admin_user.company_id
        # set country in order to format Belgian numbers
        cls.company_admin.write({
            'country_id': cls.env.ref('base.be').id,
        })

        # reference dates to have reproducible tests (sunday evening, allowing full week)
        cls.reference_now = datetime(2022, 2, 13, 20, 0, 0)
        cls.reference_monday = datetime(2022, 2, 14, 7, 0, 0)
        cls.reference_now_monthweekstart = date(2022, 1, 30)  # starts on a Sunday, first week containing Feb day
        cls.global_slots_enddate = date(2022, 3, 5)  # last day of last week of February

        cls.apt_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='apt_manager@test.example.com',
            groups='base.group_user,appointment.group_appointment_manager',
            name='Appointment Manager',
            notification_type='email',
            login='apt_manager',
            tz='Europe/Brussels'
        )
        cls.staff_user_bxls = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='brussels@test.example.com',
            groups='base.group_user',
            name='Employee Brussels',
            notification_type='email',
            login='staff_user_bxls',
            tz='Europe/Brussels'  # UTC + 1 (at least in February)
        )
        cls.staff_user_aust = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='australia@test.example.com',
            groups='base.group_user',
            name='Employee Australian',
            notification_type='email',
            login='staff_user_aust',
            tz='Australia/Perth'  # UTC + 8 (at least in February)
        )
        cls.staff_user_nz = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='new_zealand@test.example.com',
            groups='base.group_user',
            name='Employee New Zealand',
            notification_type='email',
            login='staff_user_nz',
            tz='Pacific/Auckland'  # UTC + 12
        )
        cls.staff_users = cls.staff_user_bxls + cls.staff_user_aust + cls.staff_user_nz

        # Default (test) appointment type
        # Slots are each hours from 8 to 13 (UTC + 1)
        # -> working hours: 7, 8, 9, 10 and 12 UTC as 11 is lunch time in working hours
        cls.apt_type_bxls_2days = cls.env['appointment.type'].create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'location_id': cls.staff_user_bxls.partner_id.id,
            'name': 'Bxls Appt Type',
            'max_schedule_days': 15,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'slot_ids': [
                (0, False, {'weekday': weekday,
                            'start_hour': hour,
                            'end_hour': hour + 1,
                           })
                for weekday in ['1', '2']
                for hour in range(8, 14)
            ],
            'staff_user_ids': [(4, cls.staff_user_bxls.id)],
        })

        cls.apt_type_resource = cls.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'assign_method': 'time_auto_assign',
            'min_schedule_hours': 1.0,
            'max_schedule_days': 5,
            'name': 'Test',
            'resource_manage_capacity': True,
            'schedule_based_on': 'resources',
            'slot_ids': [(0, 0, {
                'weekday': str(cls.reference_monday.isoweekday()),
                'start_hour': 15,
                'end_hour': 16,
            })],
        })

    def _test_url_open(self, url):
        """ Call url_open with nocache parameter """
        url += ('?' not in url and '?' or '&') + 'nocache'
        return self.url_open(url)

    def _create_meetings(self, user, time_info, appointment_type_id=None):
        return self.env['calendar.event'].with_context(self._test_context).create([
            {'allday': allday,
             'attendee_ids': [(0, 0, {'partner_id': user.partner_id.id})],
             'name': 'Event for %s (%s / %s - %s)' % (user.name, allday, start, stop),
             'partner_ids': [(4, user.partner_id.id)],
             'start': start,
             'stop': stop,
             'user_id': user.id,
             'appointment_type_id': appointment_type_id
            }
            for start, stop, allday in time_info
        ])

    def _create_invite_test_data(self):
        apt_type_test = self.env['appointment.type'].create({
            'name': 'Appointment Test',
        })
        self.all_apts = self.apt_type_bxls_2days + apt_type_test
        self.invite_apt_type_bxls_2days = self.env['appointment.invite'].create({
            'appointment_type_ids': self.apt_type_bxls_2days.ids,
        })
        self.invite_all_apts = self.env['appointment.invite'].create({
            'appointment_type_ids': self.all_apts.ids,
        })

    def _filter_appointment_slots(self, slots, filter_months=False, filter_weekdays=False, filter_users=False, filter_resources=False):
        """ Get all the slots info computed.
        Can target a part of slots by referencing the expected months or days we want.
        :param list slots: slots content computed from _get_appointment_slots() method.
        :param list filter_months: list of tuples representing months we want to check
            [(2, 2022), ...] where (2, 2022) represents February 2022
        :param list filter_weekdays: list of integers of the weekdays we want to check 0 = monday and 6 = sunday
            [0, 1, 3] to filter only monday, tuesday and thursday slots
        :param recordset filter_users: recordset of users for which we want to get slots when they are available
        :return list: [{
            'datetime': '2022-02-14 08:00:00',
            'duration': '1.0',
            'staff_user_id': 21,
            'hours': '08:00 - 09:00',
        }, ...] """
        slots_info = []
        for month in slots:
            # We use the last day of the first week to be sure that we use the correct month
            last_day_first_week = month['weeks'][0][-1]['day']
            month_tuple = (last_day_first_week.month, last_day_first_week.year)
            if filter_months and month_tuple not in filter_months:
                continue
            for week in month['weeks']:
                for day in week:
                    if not day['slots'] or (filter_weekdays and day['day'].weekday() not in filter_weekdays):
                        continue
                    for slot in day['slots']:
                        if filter_users and slot.get('staff_user_id') not in filter_users.ids:
                            continue
                        if filter_resources:
                            if any(slot_resource['id'] not in filter_resources.ids for slot_resource in slot.get('available_resources')):
                                continue
                        slots_info.append(slot)
        return slots_info

    def assertSlots(self, slots, exp_months, slots_data):
        """ Check slots content. Method to be improved soon, currently doing
        only basic checks. """
        self.assertEqual(len(slots), len(exp_months), 'Slots: wrong number of covered months')
        self.assertEqual(slots[0]['weeks'][0][0]['day'], slots_data['startdate'], 'Slots: wrong starting date')
        self.assertEqual(slots[-1]['weeks'][-1][-1]['day'], slots_data['enddate'], 'Slots: wrong ending date')
        for month, expected_month in zip(slots, exp_months):
            self.assertEqual(month['month'], expected_month['name_formated'])
            self.assertEqual(len(month['weeks']), expected_month['weeks_count'])
            if not slots_data.get('slots_startdate'):  # not all tests are detailed
                continue

            # global slots configuration
            slots_days_leave = slots_data.get('slots_days_leave', [])
            slots_enddate = slots_data.get('slots_enddate')
            slots_startdate = slots_data.get('slots_startdate')
            slots_weekdays_nowork = slots_data.get('slots_weekdays_nowork', [])

            # slots specific
            slots_start_hours = slots_data.get('slots_start_hours', [])

            for week in month['weeks']:
                for day in week:
                    day_date = day['day']
                    # days linked to "next month" or "previous month" are there for filling but have no slots
                    is_void = day_date.month != expected_month['month_date'].month

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
                        if day_date in slots_data.get('slots_day_specific', {}):
                            slot_count = len(slots_data['slots_day_specific'][day_date])
                            slot_start_hours = [slot['start'] for slot in slots_data['slots_day_specific'][day_date]]
                        else:
                            slot_count = len(slots_start_hours)
                            slot_start_hours = slots_start_hours
                        self.assertEqual(
                            len(day['slots']), slot_count,
                            'Slot: wrong number of slots for %s' % day
                        )
                        self.assertEqual(
                            [datetime.strptime(slot['datetime'], '%Y-%m-%d %H:%M:%S').hour for slot in day['slots']],
                            slot_start_hours,
                            'Slot: wrong starting hours'
                        )
                    elif is_void:
                        self.assertFalse(len(day['slots']), 'Slot: out of range should have no slot for %s' % day)
                    else:
                        self.assertFalse(len(day['slots']), 'Slot: not worked should have no slot for %s' % day)

    def _test_slot_generate_available_resources(self, appointment_type, asked_capacity, timezone, start_dt, end_dt, filter_resources, expected_available_resource_ids, reference_date=None):
        """ Simulate the check done after selecting a particular time slot
        :param appointment_type: appointment type tested
        :param asked_capacity<int>: asked capacity for the appointment
        :param timezone<str>: timezone selected
        :param start_dt<datetime>: start datetime of the slot (naive UTC)
        :param end_dt<datetime>: end datetime of the slot (naive UTC)
        :param filter_resources<recordset>: the resources for which the appointment was booked for
        :param expected_available_resource_ids<list>: list of resource ids available for the slot we want to check
        """
        slots = appointment_type._slots_generate(start_dt.astimezone(pytz.utc), end_dt.astimezone(pytz.utc), timezone, reference_date=reference_date)
        slots = [slot for slot in slots if slot['UTC'] == (start_dt.replace(tzinfo=None), end_dt.replace(tzinfo=None))]
        appointment_type._slots_fill_resources_availability(slots, start_dt, end_dt, filter_resources=filter_resources, asked_capacity=asked_capacity)
        self.assertEqual(set(expected_available_resource_ids), set(slots[0]['available_resource_ids'].ids))

    @contextmanager
    def mockAppointmentCalls(self):
        _original_search = Meeting.search
        _original_search_count = Meeting.search_count
        _original_calendar_verify_availability = Partner.calendar_verify_availability
        _original_work_intervals_batch = ResourceCalendar._work_intervals_batch
        with patch.object(Meeting, 'search',
                          autospec=True, side_effect=_original_search) as mock_ce_search, \
             patch.object(Meeting, 'search_count',
                          autospec=True, side_effect=_original_search_count) as mock_ce_sc, \
             patch.object(Partner, 'calendar_verify_availability',
                          autospec=True, side_effect=_original_calendar_verify_availability) as mock_partner_cal, \
             patch.object(ResourceCalendar, '_work_intervals_batch',
                          autospec=True, side_effect=_original_work_intervals_batch) as mock_cal_wit:
            self._mock_calevent_search = mock_ce_search
            self._mock_calevent_search_count = mock_ce_sc
            self._mock_partner_calendar_check = mock_partner_cal
            self._mock_cal_work_intervals = mock_cal_wit
            yield
