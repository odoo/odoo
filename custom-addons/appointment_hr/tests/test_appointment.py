# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo.addons.appointment_hr.tests.common import AppointmentHrCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged, users


class AppointmentHRLeavesTest(AppointmentHrCommon):
    @users('apt_manager', 'staff_user_bxls')
    def test_partner_on_leave_with_calendar_leave(self):
        """Check that resource leaves are correctly reflected in the partners_on_leave field.

        Overlapping times between the leave time of an employee and the meeting should add the partner
        to the list of unavailable partners.
        """
        self.env['calendar.event'].search([('user_id', '=', self.staff_user_bxls.id)]).unlink()
        self.env['resource.calendar.leaves'].sudo().search([('calendar_id', '=', self.staff_user_bxls.resource_calendar_id.id)]).unlink()
        [meeting] = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),
              self.reference_monday + timedelta(days=1, hours=3),
              False,
              )],
            self.apt_type_bxls_2days.id
        )
        self.assertFalse(meeting.partners_on_leave)
        self.env['resource.calendar.leaves'].sudo().create({
            'calendar_id': self.staff_user_bxls.resource_calendar_id.id,
            'date_from': self.reference_monday + timedelta(days=1),
            'date_to': self.reference_monday + timedelta(days=1, minutes=5),
            'name': 'Tuesday Morning Leave'
        })
        # a sane depedency cannot be expressed so it will only be updated when removed from cache
        meeting.invalidate_recordset()
        self.assertEqual(meeting.partners_on_leave, self.staff_user_bxls.partner_id)

    @users('apt_manager', 'staff_user_bxls')
    def test_partner_on_leave_with_conflicting_event(self):
        """Check that conflicting meetings are correctly reflected in the partners_on_leave field.

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
        self.assertFalse(meeting.partners_on_leave)
        [conflicting_meeting] = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday,
              self.reference_monday + timedelta(minutes=5),
              False,
              )],
        )
        meeting.invalidate_recordset()
        self.assertEqual(meeting.partners_on_leave, self.staff_user_bxls.partner_id)
        self.assertFalse(conflicting_meeting.partners_on_leave)


@tagged('appointment_slots')
class AppointmentHrTest(AppointmentHrCommon):

    @classmethod
    def setUpClass(cls):
        super(AppointmentHrTest, cls).setUpClass()
        cls.apt_type_bxls_2days.write({
            'work_hours_activated': True,
        })

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
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_midnight(self):
        """ Generates recurring slots, check around midnight """
        late_night_cal = self.env['resource.calendar'].sudo().create({
            'attendance_ids': [(0, 0, {
                'dayofweek': f'{day - 1}',
                'hour_from': hour,
                'hour_to': hour + 4,
                'name': f'Day {day} H {hour} {hour + 4}',
            }) for hour in [0, 20] for day in [1, 2, 3, 4]],
            'company_id': self.company_admin.id,
            'name': '00:00-04:00 and 20:00-00:00 on Mondays through Thursday',
            'tz': 'UTC',
        })

        # Current employee is Europe/Brussels
        current_employee_sudo = self.env.user.employee_id.sudo()
        current_employee_sudo.resource_calendar_id = late_night_cal
        current_employee_sudo.tz = 'UTC'

        apt_type = self.env['appointment.type'].create({
            'appointment_duration': 1,
            'appointment_tz': 'UTC',
            'category': 'recurring',
            'name': 'Midnight Test',
            'max_schedule_days': 4,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 0,
            'slot_ids': [
                (0, False, {'weekday': '1',
                            'start_hour': hour,
                            'end_hour': (hour + 1) % 24,
                           })
                for hour in [0, 1, 2, 21, 22, 23]
            ] + [
                (0, False, {'weekday': '2',
                            'start_hour': hour,
                            'end_hour': hour + 1,
                           })
                for hour in [0, 1, 2]
            ] + [
                (0, False, {'weekday': '2',
                            'start_hour': 20,
                            'end_hour': 00,
                           })
            ] + [
                (0, False, {'weekday': '3',
                            'start_hour': hour,
                            'end_hour': (hour + 5) % 24,
                           })
                for hour in [0, 19]
            ],
            'staff_user_ids': self.env.user.ids,
            'work_hours_activated': True,
        })

        # freeze the day before, early enough to be able to schedule the first hour
        with freeze_time(self.reference_monday.replace(hour=1, minute=36)):
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
             'slots_day_specific': {self.reference_monday.date(): [
                    {'start': 2, 'end': 3},  # 02:00 is the first valid slot when the current time is 01:36
                    {'start': 21, 'end': 22},
                    {'start': 22, 'end': 23},
                    {'start': 23, 'end': 00},
                ], (self.reference_monday + timedelta(days=1)).date(): [
                    {'start': 0, 'end': 1},
                    {'start': 1, 'end': 2},
                    {'start': 2, 'end': 3},
                    {'start': 20, 'end': 21},
                    {'start': 21, 'end': 22},
                    {'start': 22, 'end': 23},
                    {'start': 23, 'end': 00},
                ], (self.reference_monday + timedelta(days=2)).date(): [
                    {'start': 0, 'end': 1},
                    {'start': 1, 'end': 2},
                    {'start': 2, 'end': 3},
                    {'start': 3, 'end': 4},  # slots start at 20 and end at 4 because of resource schedule
                    {'start': 20, 'end': 21},
                    {'start': 21, 'end': 22},
                    {'start': 22, 'end': 23},
                    {'start': 23, 'end': 00},
                ]},
             'slots_startdate': self.reference_monday,
            }
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
             'slots_start_hours': [7, 8, 9, 10, 12],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_wleaves(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create personal leaves
        _leaves = self._create_leaves(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 2 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=2)),
             (self.reference_monday + timedelta(days=7), # next Monday: one hour
              self.reference_monday + timedelta(days=7, hours=1))
            ],
        )
        # add global leaves
        _leaves += self._create_leaves(
            self.env['res.users'],
            [(self.reference_monday + timedelta(days=8), # next Tuesday is bank holiday
              self.reference_monday + timedelta(days=8, hours=12))
            ],
            calendar=self.staff_user_bxls.resource_calendar_id,
        )

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
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-9 UTC
                (self.reference_monday + timedelta(days=7)).date(): [
                    {'end': 10, 'start': 9},
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-8
                (self.reference_monday + timedelta(days=8)).date(): [],  # 12 hours long bank holiday
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

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
                    {'end': 14, 'start': 13},
                ],  # meetings on 7-10 UTC
                (self.reference_monday + timedelta(days=7)).date(): [],  # on meeting "allday"
                (self.reference_monday + timedelta(days=8)).date(): [
                    {'end': 9, 'start': 8},
                    {'end': 10, 'start': 9},
                    {'end': 12, 'start': 11},
                ],  # meetings 9-10 and 12-14
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )
