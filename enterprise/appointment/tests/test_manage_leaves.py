# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.tests import users
from odoo.addons.appointment.tests.common import AppointmentCommon


class AppointmentManageLeaveTest(AppointmentCommon):

    @users('apt_manager')
    def test_manage_leaves(self):
        """Check the resource leaves wizard works"""
        start_monday = datetime(2022, 2, 14, 0, 0, 0)
        start_leave = datetime(2022, 2, 14, 14, 0, 0)
        stop_leave = datetime(2022, 2, 14, 15, 0, 0)

        calendar = self.env['resource.calendar'].sudo().create({
            'company_id': False,
            'attendance_ids': [
                (0, 0, {'dayofweek': str(weekday),
                        'day_period': 'morning',
                        'hour_from': 8,
                        'hour_to': 18,
                        'name': 'Day %s H 8 18',
                        })
                for weekday in range(7)
            ],
            'name': 'Test Calendar',
            'tz': 'UTC'
        })
        # Set user to be the same date so HR override on resource leaves doesn't modify dates
        self.env.user.sudo().tz = 'UTC'
        resources = self.env['appointment.resource'].create([{
            'capacity': 1,
            'name': f'Test Resource {res_id}',
            'resource_calendar_id': calendar.id,
        } for res_id in range(1, 4)])
        appt_type = self.env['appointment.type'].create({
            'category': 'recurring',
            'name': 'Book a tennis court',
            'max_schedule_days': 1,
            'appointment_duration': 1,
            'appointment_tz': 'Europe/Brussels',
            'slot_ids': [(0, 0, {
                'weekday': '1',  # Monday
                'start_hour': 9,
                'end_hour': 17,
            })],
            'resource_ids': resources.ids,
            'schedule_based_on': 'resources',
            'assign_method': 'time_resource',
        }).with_user(self.env.user)

        with freeze_time(start_monday):
            slots = appt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = datetime(2022, 1, 30).date()
        global_slots_enddate = datetime(2022, 3, 5).date()
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
              }
             ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [hour for hour in range(9, 17)],
             'slots_startdate': start_monday.date(),
             'slots_enddate': start_monday.date(),
             }
        )
        for slot_resources in [resource['available_resources'] for resource in self._filter_appointment_slots(slots)]:
            self.assertEqual(set(slot_resource['id'] for slot_resource in slot_resources), set(resources.ids))

        self.env['appointment.manage.leaves'].create({
            'appointment_resource_ids': resources[0],
            'leave_start_dt': start_leave,
            'leave_end_dt': stop_leave,
        }).action_create_leave()

        with freeze_time(start_monday):
            slots = appt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
              }
             ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [hour for hour in range(9, 17)],
             'slots_startdate': start_monday.date(),  # first Monday after reference_now
             'slots_enddate': start_monday.date(),  # only test that day
             }
        )
        available_resources_14h = [resource['id'] for resource in self._filter_appointment_slots(slots)[14 - 9]['available_resources']]
        available_resources_15h = [resource['id'] for resource in self._filter_appointment_slots(slots)[15 - 9]['available_resources']]
        available_resources_16h = [resource['id'] for resource in self._filter_appointment_slots(slots)[16 - 9]['available_resources']]
        self.assertEqual(set(available_resources_14h), set(resources.ids))
        self.assertEqual(set(available_resources_15h), set((resources - resources[0]).ids), 'Resource should be on leave and excluded from slots')
        self.assertEqual(set(available_resources_16h), set(resources.ids))

        # Global calendar leave
        self.env['resource.calendar.leaves'].sudo().create({
            'calendar_id': calendar.id,
            'date_from': start_leave,
            'date_to': stop_leave,
        }).company_id = False

        with freeze_time(start_monday):
            slots = appt_type._get_appointment_slots('Europe/Brussels')

        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
              }
             ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [hour for hour in range(9, 15)] + [hour for hour in range(16, 17)],
             'slots_startdate': start_monday.date(),  # first Monday after reference_now
             'slots_enddate': start_monday.date(),  # only test that day
             }
        )

        # From here: Test last day availability.
        # BXL TZ: Work hours 9h -> 19h / Appt slots 9h -> 21h / Leave on resources' calendar 15h -> 16h
        start_sunday = datetime(2022, 2, 13, 7, 0, 0)
        appt_type.slot_ids.end_hour = 21

        # 9 Available slots: 9h -> 15h and 16h -> 19h
        with freeze_time(start_sunday):
            slots = appt_type._get_appointment_slots('Europe/Brussels')
        self.assertEqual(len(self._filter_appointment_slots(slots)), 9, 'Leaves, bookings and work hours should be taken into account on last day')

        # Test with NOW in different days: 22h SAT UTC / 11h SUN NZ
        # Work hours: 4h -> 7h UTC / 17h -> 20h NZ
        # Appt slots: 4h -> 8h UTC / 17h -> 21h NZ
        start_saturday_UTC = datetime(2022, 2, 12, 22, 0, 0)
        calendar.attendance_ids.write({'hour_from': 4, 'hour_to': 7})
        appt_type.appointment_tz = 'Pacific/Auckland'
        appt_type.slot_ids.start_hour = 17
        self.env['calendar.event'].create([{
            'name': 'Resource Test Booking',
            'appointment_type_id': appt_type.id,
            'booking_line_ids': [(0, 0, {
                'appointment_resource_id': resource.id,
                'capacity_reserved': 1,
                'capacity_used': 1,
            }) for resource in appt_type.resource_ids],
            'start': datetime(2022, 2, 14, 4, 0, 0),
            'stop': datetime(2022, 2, 14, 5, 0, 0),
        }])
        self.env['appointment.manage.leaves'].sudo().create({
            'appointment_resource_ids': resources.ids,
            'leave_start_dt': datetime(2022, 2, 14, 5, 0, 0),
            'leave_end_dt': datetime(2022, 2, 14, 6, 0, 0),
        }).action_create_leave()

        # 1 Available appt slot: 6h -> 7h UTC. Other ones are booked / on leave / outside work hours.
        with freeze_time(start_saturday_UTC):
            slots = appt_type._get_appointment_slots('UTC')
        self.assertEqual(len(self._filter_appointment_slots(slots)), 1, 'Leaves, bookings and work hours should be taken into account on last day')
