# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

from odoo.tests import new_test_user, tagged
from .test_ui_common import TestUiCommon


@tagged('-at_install', 'post_install')
class TestUi(TestUiCommon):
    def test_01_ui(self):
        self.start_tour("/", 'planning_test_tour', login='admin')

    def test_shift_switch_ui(self):
        bert_user = new_test_user(self.env,
                                  login='bert_user',
                                  groups='planning.group_planning_user',
                                  name='Bert User',
                                  email='user@example.com')
        bety_user = new_test_user(self.env,
                                    login='bety_user',
                                    groups='planning.group_planning_user',
                                    name='Bety User',
                                    email='buser@example.com')
        test_role = self.env["planning.role"].create([{'name': 'test_role'}])
        employee_bert, employee_bety = self.env['hr.employee'].create([
            {
                'name': 'bert',
                'work_email': 'bert@a.be',
                'tz': 'UTC',
                'employee_type': 'freelance',
                'create_date': '2015-01-01 00:00:00',
                'user_id': bert_user.id,
                'planning_role_ids': test_role,
            },
            {
                'name': 'bety',
                'work_email': 'bety@a.be',
                'tz': 'UTC',
                'employee_type': 'freelance',
                'create_date': '2015-01-01 00:00:00',
                'user_id': bety_user.id,
                'planning_role_ids': test_role,
            }
        ])
        test_slot = self.env['planning.slot'].create({
            'start_datetime': datetime.now(),
            'end_datetime': datetime.now() + relativedelta(hours=1),
            'state': 'published',
            'resource_id': employee_bert.resource_id.id,
        })
        self.assertEqual(test_slot.request_to_switch, False, 'Before requesting to switch, the request to switch should be False')
        self.start_tour("/", 'planning_shift_switching_backend', login='bert_user')
        self.assertEqual(test_slot.request_to_switch, True, 'Before requesting to switch, the request to switch should be False')
        self.start_tour("/", 'planning_assigning_unwanted_shift_backend', login='admin')
        self.assertEqual(test_slot.request_to_switch, False, 'After the assign action, the request to switch should be False')
        self.assertEqual(test_slot.resource_id, employee_bety.resource_id, 'The shift should now be assigned to Bety')

    def test_planning_no_email(self):
        aaron_role = self.env["planning.role"].create([{'name': 'aaron_role'}])
        employee_thibault_user = new_test_user(self.env,
            login='thibault_user',
            groups='planning.group_planning_user',
            name='Thibault User',
            email=None
        )
        self.employee_thibault.write({
            "user_id": employee_thibault_user.id,
            "planning_role_ids": aaron_role,
        })
        self.env['planning.slot'].create({
            'start_datetime': datetime.now(),
            'end_datetime': datetime.now() + relativedelta(hours=1),
            'resource_id': self.employee_thibault.resource_id.id,
        })
        self.start_tour("/", 'planning_test_tour_no_email', login='admin')

    def test_split_shift_ui(self):
        PlanningSlot = self.env['planning.slot']
        # create a user with planning manager rights and timezone set to UTC
        hugo = new_test_user(
            self.env,
            login='hugo_user',
            groups='planning.group_planning_manager',
            name='Hugo',
            email='hugo@example.com',
            tz='UTC',
        )
        # 1. Creating work schedule in UTC
        attendance_schedule = { # To round to hours!
            'start_am': time.fromisoformat('08:00:00'),
            'end_am': time.fromisoformat('12:00:00'),
            'start_pm': time.fromisoformat('13:00:00'),
            'end_pm': time.fromisoformat('17:00:00'),
        }
        work_schedule_calendar = self.env['resource.calendar'].create([{
            'name': 'Musketeers schedule (UTC)',
            'tz': 'UTC',
        }])
        self.env['resource.calendar.attendance'].create([
            {
                'name': 'Wednesday AM',
                'dayofweek': '2',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Wednesday PM',
                'dayofweek': '2',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Thursday AM',
                'dayofweek': '3',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Thursday PM',
                'dayofweek': '3',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Friday AM',
                'dayofweek': '4',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Friday PM',
                'dayofweek': '4',
                'hour_from': attendance_schedule['start_am'].hour,
                'hour_to': attendance_schedule['end_am'].hour,
                'calendar_id': work_schedule_calendar.id,
            },
        ])

        # 2. Creating employees using those work schedules
        employees = (
            employee_aramis,
            employee_athos,
            employee_porthos,
        ) = self.env['hr.employee'].create([
            {
                'name': 'Aramis',
                'resource_calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Athos',
                'resource_calendar_id': work_schedule_calendar.id,
            },
            {
                'name': 'Porthos',
                'resource_calendar_id': work_schedule_calendar.id,
            },
        ])

        # 3. Creating shifts for those employees (in UTC)
        days_to_wednesday = 2 - date.today().weekday() + 7 * (date.today().weekday() // 6)
        start_date = date.today() + relativedelta(days=days_to_wednesday)
        end_date = start_date + relativedelta(days=2)
        start_date_normal = datetime.combine(start_date, attendance_schedule['start_am'])
        start_date_late = datetime.combine(start_date, attendance_schedule['end_pm']) + relativedelta(hours=3)
        end_date_normal = datetime.combine(end_date, attendance_schedule['end_pm'])
        end_date_early = datetime.combine(end_date, attendance_schedule['start_am']) - relativedelta(hours=2)

        full_slot_aramis, full_slot_athos, _ = PlanningSlot.with_user(hugo).create([
            {
                'start_datetime': start_date_normal,
                'end_datetime': end_date_normal,
                'state': 'published',
                'resource_id': employee_aramis.resource_id.id,
            },
            {
                'start_datetime': start_date_late,
                'end_datetime': end_date_early,
                'state': 'published',
                'resource_id': employee_athos.resource_id.id,
            },
            {
                'start_datetime': start_date_normal,
                'end_datetime': end_date_normal,
                'state': 'published',
                'resource_id': employee_porthos.resource_id.id,
                'repeat': True,
                'repeat_unit': 'week',
                'repeat_interval': 1,
                'repeat_type': 'x_times',
                'repeat_number': 3,
            },
        ])
        # Initially 1 slot assigned to Aramis, 1 to Athos and 3 to Porthos
        slot_count_per_resource = dict(PlanningSlot._read_group(
            [('resource_id', 'in', employees.resource_id.ids)],
            ['resource_id'], ['__count'],
        ))
        self.assertDictEqual(slot_count_per_resource, {
            employee_aramis.resource_id: 1,
            employee_athos.resource_id: 1,
            employee_porthos.resource_id: 3,
        })

        # 4. Launching tour (Browser in UTC by default)
        self.start_tour("/", 'planning_split_shift_week', login='hugo_user')

        # 5. Verify the resulting slots after splitting
        slot_data = PlanningSlot.search_read(
            [('resource_id', 'in', employees.resource_id.ids)],
            fields=['resource_id', 'start_datetime', 'end_datetime'],
            order='start_datetime ASC',
            load=False,
        )
        slots_per_resource_id = defaultdict(list)
        for slot in slot_data:
            slots_per_resource_id[slot['resource_id']].append(slot)
        slots_aramis, slots_athos, slots_porthos = (
            slots_per_resource_id[employee.resource_id.id]
            for employee in employees
        )
        # After splitting: 2 slot assigned to Aramis, 3 to Athos and 4 to Porthos
        self.assertEqual(len(slots_aramis), 2)
        self.assertEqual(len(slots_athos), 3)
        self.assertEqual(len(slots_porthos), 4, "Splitting a recurrent shift should only split one occurrence")
        self.assertEqual([slots_aramis[0]['start_datetime'], slots_aramis[0]['end_datetime']], [start_date_normal, start_date_normal + relativedelta(hours=9)],
                         "When splitting a shift planned during resource's work schedule, resulting shifts should not start or end outside of this schedule.")
        self.assertEqual([slots_aramis[1]['start_datetime'], slots_aramis[1]['end_datetime']], [start_date_normal + relativedelta(days=1), end_date_normal],
                         "When splitting a shift planned during resource's work schedule, resulting shifts should not start or end outside of this schedule.")
        self.assertEqual([slots_athos[0]['start_datetime'], slots_athos[0]['end_datetime']], [start_date_late, start_date_late + relativedelta(seconds=1)],
                         "When splitting a shift starting after end of resource's work schedule at the end of the first day, first resulting shift should end one second after it starts.")
        self.assertEqual([slots_athos[2]['start_datetime'], slots_athos[2]['end_datetime']], [end_date_early - relativedelta(seconds=1), end_date_early],
                         "When splitting a shift ending before the start of resource's work schedule at the end of the penultimate day, last resulting shift should start one second before it ends.")
        self.assertEqual([slots_porthos[2]['start_datetime'], slots_porthos[2]['end_datetime']], [start_date_normal + relativedelta(weeks=1), end_date_normal + relativedelta(weeks=1)],
                         "Splitting a recurrent shift should only split one occurrence")

        # 6. Undo the splits
        # One split was done on the slot of Aramis, we undo it and check that the dates of the resulting slot correspond to the ones we had before the split
        slot1_aramis, slot2_aramis = PlanningSlot.browse([slot['id'] for slot in slots_aramis])
        (slot1_aramis + slot2_aramis).undo_split_shift(full_slot_aramis.start_datetime, full_slot_aramis.end_datetime, slot1_aramis.resource_id)
        self.assertFalse(slot2_aramis.exists())
        self.assertEqual([slot1_aramis.start_datetime, slot1_aramis.end_datetime], [full_slot_aramis.start_datetime, full_slot_aramis.end_datetime])

        # Two splits were done on the slot of Athos, we first undo the second split (between part 1 and part 2 of the slot)
        slot1_athos, slot2_athos, slot3_athos = PlanningSlot.browse([slot['id'] for slot in slots_athos])
        slot_athos12_start_date = slot1_athos.start_datetime
        slot_athos12_end_datetime = slot2_athos.end_datetime
        (slot1_athos + slot2_athos).undo_split_shift(slot_athos12_start_date, slot_athos12_end_datetime, slot1_athos.resource_id)
        self.assertFalse(slot2_athos.exists())
        self.assertEqual([slot1_athos.start_datetime, slot1_athos.end_datetime], [slot_athos12_start_date, slot_athos12_end_datetime])
        # We then undo the first split (between resulting part and part 3 of the slot)
        (slot1_athos + slot3_athos).undo_split_shift(full_slot_athos.start_datetime, full_slot_athos.end_datetime, slot1_athos.resource_id)
        self.assertFalse(slot3_athos.exists())
        self.assertEqual([slot1_athos.start_datetime, slot1_athos.end_datetime], [full_slot_athos.start_datetime, full_slot_athos.end_datetime])

    def test_onboarding_tour(self):
        self.start_tour("/odoo", 'planning_tour', login='admin')
