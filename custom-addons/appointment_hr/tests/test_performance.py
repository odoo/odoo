# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import time

from datetime import date, timedelta
from freezegun import freeze_time
from logging import getLogger

from odoo.addons.appointment_hr.tests.common import AppointmentHrCommon
from odoo.addons.appointment.tests.test_performance import AppointmentPerformanceCase, AppointmentUIPerformanceCase
from odoo.tests import tagged, users
from odoo.tests.common import warmup

_logger = getLogger(__name__)


class AppointmenHrPerformanceCase(AppointmentHrCommon, AppointmentPerformanceCase):

    @classmethod
    def setUpClass(cls):
        super(AppointmenHrPerformanceCase, cls).setUpClass()

        cls.test_calendar = cls.env['resource.calendar'].create({
            'company_id': cls.company_admin.id,
            'name': 'Test Calendar',
            'tz': 'Europe/Brussels',
        })

        cls.staff_users = cls.env['res.users'].with_context(cls._test_context).create([
            {'company_id': cls.company_admin.id,
             'company_ids': [(4, cls.company_admin.id)],
             'email': 'brussels.%s@test.example.com' % idx,
             'groups_id': [(4, cls.env.ref('base.group_user').id)],
             'name': 'Employee Brussels %s' % idx,
             'login': 'staff_users_bxl_%s' % idx,
             'notification_type': 'email',
             'tz': 'Europe/Brussels',
            } for idx in range(20)
        ])
        cls.resources = cls.env['appointment.resource'].create([
            {'name': 'Resource %s' % idx} for idx in range(20)
        ])

        # User resources and employees
        cls.staff_users_resources = cls.env['resource.resource'].create([
            {'calendar_id': cls.test_calendar.id,
             'company_id': user.company_id.id,
             'name': user.name,
             'user_id': user.id,
             'tz': user.tz,
            } for user in cls.staff_users
        ])
        cls.staff_users_employees = cls.env['hr.employee'].create([
            {'company_id': user.company_id.id,
             'resource_calendar_id': cls.test_calendar.id,
             'resource_id': cls.staff_users_resources[user_idx].id,
            } for user_idx, user in enumerate(cls.staff_users)
        ])

        # Events and leaves
        cls.test_events = cls.env['calendar.event'].with_context(cls._test_context).create([
            {'attendee_ids': [(0, 0, {'partner_id': user.partner_id.id})],
             'name': 'Event for %s' % user.name,
             'partner_ids': [(4, user.partner_id.id)],
             'start': cls.reference_monday + timedelta(weeks=week_idx, days=day_idx, hours=(user_idx / 4)),
             'stop': cls.reference_monday + timedelta(weeks=week_idx, days=day_idx, hours=(user_idx / 4) + 1),
             'user_id': user.id,
            }
            for day_idx in range(5)
            for week_idx in range(5)
            for user_idx, user in enumerate(cls.staff_users)
        ])
        cls.test_leaves = cls.env['resource.calendar.leaves'].with_context(cls._test_context).create([
            {'calendar_id': user.resource_calendar_id.id,
             'company_id': user.company_id.id,
             'date_from': cls.reference_monday + timedelta(weeks=week_idx * 2, days=(user_idx / 4), hours=2),
             'date_to': cls.reference_monday + timedelta(weeks=week_idx * 2, days=(user_idx / 4), hours=8),
             'name': 'Leave for %s' % user.name,
             'resource_id': user.resource_ids[0].id,
             'time_type': 'leave',
            }
            for week_idx in range(5)  # one leave every 2 weeks
            for user_idx, user in enumerate(cls.staff_users)
        ])

        cls.test_apt_type = cls.env['appointment.type'].create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'recurring',
            'max_schedule_days': 60,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'name': 'Test Appointment Type',
            'schedule_based_on': 'users',
            'slot_ids': [
                (0, 0, {'end_hour': hour + 1,
                        'start_hour': hour,
                        'weekday': weekday,
                        })
                for weekday in ['1', '2', '3', '4', '5']
                for hour in range(8, 16)
            ],
            'staff_user_ids': [(4, user.id) for user in cls.staff_users],
            'work_hours_activated': True,
        })
        cls.test_appointment_location = cls.env['res.partner'].create({
            'name': 'Bxls Office',
            'street': 'Rue Haute 63'
        })


@tagged('appointment_performance', 'post_install', '-at_install')
class AppointmentPerformanceTest(AppointmenHrPerformanceCase):

    def setUp(self):
        super().setUp()
        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

    def test_appointment_initial_values(self):
        """ Check initial values to ease understanding and reproducing tests. """
        self.assertEqual(len(self.test_apt_type.slot_ids), 40)
        self.assertTrue(all(employee.resource_id for employee in self.staff_users_employees))
        self.assertTrue(all(employee.resource_id.calendar_id for employee in self.staff_users_employees))
        self.assertTrue(all(employee.user_id for employee in self.staff_users_employees))

    @users('staff_user_bxls')
    def test_get_appointment_slots_anytime(self):
        """ Any time type: mono user, involved work hours check. """
        self.apt_type_bxls_2days.write({
            'category': 'anytime',
            'max_schedule_days': 90,
            'slot_ids': [(5, 0)] + [  # while loop in _slots_generate generates the actual slots
                (0, 0, {'end_hour': 0,  # 0 hour of next day
                        'start_hour': hour * 0.5,
                        'weekday': str(day + 1),
                       }
                )
                for hour in range(2)
                for day in range(7)
            ],
            'staff_user_ids': [(5, 0), (4, self.staff_users[0].id)],
            'work_hours_activated': True,
            })
        self.env.flush_all()
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=40):  # apt_hr 36
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~3.40
        # Time after optimization: ~0.45
        # Method count before optimization: 4186 - 4186 - 4186 - 1
        # Method count after optimization: 1 - 0 - 0 - 1

        global_slots_enddate = date(2022, 6, 4)  # last day of last week of May
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 27/02 -> 27/03 (02/04)
             },
             {'name_formated': 'April 2022',
              'weeks_count': 5,
             },
             {'name_formated': 'May 2022',
              'weeks_count': 5,
             },
            ],
            {'enddate': global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_anytime_short(self):
        """ Any time type: mono user, involved any time check. """
        self.apt_type_bxls_2days.write({
            'category': 'anytime',
            'max_schedule_days': 10,
            'slot_ids': [(5, 0)] + [  # while loop in _slots_generate generates the actual slots
                (0, 0, {'end_hour': 0,  # 0 hour of next day
                        'start_hour': hour * 0.5,
                        'weekday': str(day + 1),
                       }
                )
                for hour in range(2)
                for day in range(7)
            ],
            'staff_user_ids': [(5, 0), (4, self.staff_users[0].id)],
            'work_hours_activated': True,
        })
        self.env.flush_all()
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=40):  # apt_hr 36
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.50
        # Time before optimization: ~0.07
        # Method count before optimization: 506 - 506 - 506 - 1
        # Method count after optimization: 1 - 0 - 0 - 1

        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_custom(self):
        """ Custom type: mono user, unique slots, work hours check. """
        apt_type_custom_bxls = self.env['appointment.type'].sudo().create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'custom',
            'location_id': self.test_appointment_location.id,
            'name': 'Bxls Appt Type',
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'max_schedule_days': 30,
            'slot_ids': [
                (0, 0, {'end_datetime': self.reference_monday + timedelta(days=day, hours=hour + 1),
                        'start_datetime': self.reference_monday + timedelta(days=day, hours=hour),
                        'slot_type': 'unique',
                        'weekday': '1',  # not used actually
                       }
                )
                for day in range(30)
                for hour in range(8, 16)
            ],
            'staff_user_ids': [(4, self.staff_users[0].id)],
            'work_hours_activated': False,
        })
        self.env.flush_all()
        apt_type_custom_bxls = apt_type_custom_bxls.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=23):  # runbot: 22
            t0 = time.time()
            res = apt_type_custom_bxls._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.45
        # Time after optimization: ~0.04
        # Method count before optimization: 480 - 480 - 480 - 1
        # Method count after optimization: 1 - 0 - 0 - 0

        global_slots_enddate = date(2022, 4, 2)  # last day of last week of May
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 27/02 -> 27/03 (02/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_custom_whours(self):
        """ Custom type: mono user, unique slots, work hours check. """
        apt_type_custom_bxls = self.env['appointment.type'].sudo().create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'time_auto_assign',
            'category': 'custom',
            'location_id': self.test_appointment_location.id,
            'name': 'Bxls Appt Type',
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'max_schedule_days': 30,
            'slot_ids': [
                (0, 0, {'end_datetime': self.reference_monday + timedelta(days=day, hours=hour + 1),
                        'start_datetime': self.reference_monday + timedelta(days=day, hours=hour),
                        'slot_type': 'unique',
                        'weekday': '1',  # not used actually
                       }
                )
                for day in range(30)
                for hour in range(8, 16)
            ],
            'staff_user_ids': [(4, self.staff_users[0].id)],
            'work_hours_activated': True,
        })
        self.env.flush_all()
        apt_type_custom_bxls = apt_type_custom_bxls.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=23):  # runbot: 22
            t0 = time.time()
            res = apt_type_custom_bxls._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.48
        # Time after optimization: ~0.04
        # Method count before optimization: 480 - 480 - 480 - 1
        # Method count after optimization: 1 - 0 - 0 - 0

        global_slots_enddate = date(2022, 4, 2)  # last day of last week of May
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 27/02 -> 27/03 (02/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_website(self):
        """ Website type: multi users (choose first available), without working
        hours. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability
        self.test_apt_type.write({'work_hours_activated': False})
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=45):  # apt_hr 42
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~1.0
        # Time before optimization: ~0.15
        # Method count before optimization: 402 - 402 - 402 - 20
        # Method count after optimization: 1 - 0 - 0 - 0

        global_slots_enddate = date(2022, 4, 30)  # last day of last week of April
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 27/02 -> 27/03 (02/04)
             },
             {'name_formated': 'April 2022',
              'weeks_count': 5,  # 27/03 -> 24/04 (30/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'slots_duration': 1,
             'slots_hours': range(8, 16, 1),
             'slots_startdt': self.reference_monday,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_website_whours(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=58):  # apt_hr 51
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~1.8
        # Time after optimization: ~0.25
        # Method count before optimization: 1261 - 1261 - 1261 - 20
        # Method count after optimization: 1 - 0 - 0 - 1

        global_slots_enddate = date(2022, 4, 30)  # last day of last week of April
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 27/02 -> 27/03 (02/04)
             },
             {'name_formated': 'April 2022',
              'weeks_count': 5,  # 27/03 -> 24/04 (30/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'slots_duration': 1,
             'slots_hours': range(8, 16, 1),
             'slots_startdt': self.reference_monday,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_website_whours_short(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability
        self.test_apt_type.write({'max_schedule_days': 10})
        self.env.flush_all()
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=58):  # apt_hr 51
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.35
        # Time after optimization: ~0.08
        # Method count before optimization: 237 - 237 - 237 - 20
        # Method count after optimization: 1 - 0 - 0 - 1

        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )

    @warmup
    @users('staff_user_bxls')
    def test_get_appointment_slots_website_whours_short_warmup(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability
        self.test_apt_type.write({'max_schedule_days': 10})
        self.env.flush_all()
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=29):
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.35
        # Time before optimization: ~0.07
        # Method count before optimization: 237 - 237 - 237 - 20
        # Method count after optimization: 1 - 0 - 0 - 1

        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 30/01 -> 27/02 (05/03)
             }
            ],
            {'enddate': self.global_slots_enddate,
             'startdate': self.reference_now_monthweekstart,
            }
        )


@tagged('appointment_performance', 'post_install', '-at_install')
class OnlineAppointmentPerformance(AppointmentUIPerformanceCase, AppointmenHrPerformanceCase):

    def setUp(self):
        super().setUp()
        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

    @warmup
    def test_appointment_type_page_anytime(self):
        """ Any time type: mono user, involved any time check. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability

        self.test_apt_type.write({
            'category': 'anytime',
            'max_schedule_days': 90,
            'slot_ids': [(5, 0)] + [  # while loop in _slots_generate generates the actual slots
                (0, 0, {'end_hour': 0,  # 0 hour of next day
                        'start_hour': hour * 0.5,
                        'weekday': str(day + 1),
                       }
                )
                for hour in range(2)
                for day in range(7)
            ],
            'staff_user_ids': [(5, 0), (4, self.staff_users[0].id)],
            })
        self.env.flush_all()

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=52):  # apt_hr 39 / +1 for no-demo
                self._test_url_open('/appointment/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~4.60 (but with boilerplate)
        # Time after optimization: ~1.10 (but with boilerplate)

    @warmup
    def test_appointment_type_page_website_whours_user(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_fill_users_availability

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=50):  # apt_hr 37 / +1 for no-demo
                self._test_url_open('/appointment/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /appointment/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~1.90 (but with boilerplate)
        # Time after optimization: ~0.50 (but with boilerplate)
