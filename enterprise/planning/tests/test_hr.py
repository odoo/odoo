# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from freezegun import freeze_time
import pytz

from odoo import fields

from odoo.addons.resource.models.utils import Intervals
from .common import TestCommonPlanning

class TestPlanningHr(TestCommonPlanning):
    @classmethod
    def setUpClass(cls):
        super(TestPlanningHr, cls).setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.Datetime.now)
        with freeze_time('2015-1-1'):
            cls.setUpEmployees()
        calendar_joseph = cls.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 13, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 14, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 14, 'hour_to': 18, 'day_period': 'afternoon'}),
            ]
        })
        cls.employee_joseph.resource_calendar_id = calendar_joseph

    def test_change_default_planning_role(self):
        self.assertFalse(self.employee_joseph.default_planning_role_id, "Joseph should have no default planning role")
        self.assertFalse(self.employee_joseph.planning_role_ids, "Joseph should have no planning roles")

        role_a = self.env['planning.role'].create({
            'name': 'role a'
        })
        role_b = self.env['planning.role'].create({
            'name': 'role b'
        })

        self.employee_joseph.default_planning_role_id = role_a

        self.assertEqual(self.employee_joseph.default_planning_role_id, role_a, "Joseph should have role a as default role")
        self.assertTrue(role_a in self.employee_joseph.planning_role_ids, "role a should be added to his planning roles")

        self.employee_joseph.write({'planning_role_ids': [(5, 0, 0)]})
        self.assertFalse(self.employee_joseph.planning_role_ids, "role a should be automatically removed from his planning roles")

        self.employee_joseph.write({'planning_role_ids': role_a})
        self.employee_joseph.default_planning_role_id = role_b
        self.assertTrue(role_a in self.employee_joseph.planning_role_ids, "role a should still be in planning roles")
        self.assertTrue(role_b in self.employee_joseph.planning_role_ids, "role b should be added to planning roles")

    def test_relation_employee_role_ids_resource_id_role_ids(self):

        """
            This test checks that the fields employee.planning_role_ids, employee.default_planning_role_id and employee.resource_id.role_ids
            are all consistent and properly update on the change of the fields. Here's the expected behavior :
            Invariant :
                resource_id.role_ids = planning_role_ids
                default_planning_role_id in planning_role_ids
            on planning_role_ids update :
                resource_id.role_ids is set accordingly.
                if planning_role_ids is set to False, set default_role_id to False
                if default_role_id is not in planning_role_ids anymore, set default_role_id to planning_role_ids[0]
            on resource_id.role_ids update :
                planning_role_ids is set accordingly.
                if planning_role_ids is set to False, set default_role_id to False
                if default_role_id is not in planning_role_ids anymore, set default_role_id to planning_role_ids[0]
            on default_planning_role_id update:
                if default_planning_role_id not in planning_role_ids, add default_planning_role_id to planning_role_ids and resource_id.role_ids
                default_planning_role_id is not removed from planning_role_ids
                if planning_role_ids is set to False in the same write as the change of default_planning_role_id, both the fields are set to False
        """
        self.assertFalse(self.employee_joseph.default_planning_role_id, "Joseph should have no default planning role")
        self.assertFalse(self.employee_joseph.planning_role_ids, "Joseph should have no planning roles")

        role_a, role_b, role_c = self.env['planning.role'].create([
            {'name': 'role a'},
            {'name': 'role b'},
            {'name': 'role c'},
        ])

        roles = self.env['planning.role']
        roles |= role_a
        roles |= role_b
        roles |= role_c
        # change on employee.planning_role_ids
        self.employee_joseph.planning_role_ids = roles
        self.assertEqual(self.employee_joseph.default_planning_role_id, role_a, "Joseph should have role a as default role")
        self.assertEqual(self.employee_joseph.resource_id.role_ids, roles, "Joseph should have role a, b and c as roles")
        self.assertEqual(self.employee_joseph.planning_role_ids, roles, "Joseph should have role a, b and c as resource_id.role_ids")

        self.employee_joseph.planning_role_ids = False
        self.assertFalse(self.employee_joseph.default_planning_role_id, "Joseph should have role a as default role")
        self.assertFalse(self.employee_joseph.resource_id.role_ids, "Joseph should have role a, b and c as roles")
        self.assertFalse(self.employee_joseph.planning_role_ids, "Joseph should have role a, b and c as resource_id.role_ids")

        #change on employee.resource_id.role_ids
        self.employee_joseph.resource_id.role_ids = roles
        self.assertEqual(self.employee_joseph.resource_id.role_ids, roles, "Joseph should have role a, b and c as roles")
        self.assertEqual(self.employee_joseph.default_planning_role_id, role_a, "Joseph should have role a as default role")
        self.assertEqual(self.employee_joseph.planning_role_ids, roles, "Joseph should have role a, b and c as resource_id.role_ids")

        self.employee_joseph.resource_id.role_ids = False
        self.assertFalse(self.employee_joseph.resource_id.role_ids, "Joseph should have role a, b and c as roles")
        self.assertFalse(self.employee_joseph.default_planning_role_id, "Joseph should have role a as default role")
        self.assertFalse(self.employee_joseph.planning_role_ids, "Joseph should have role a, b and c as resource_id.role_ids")

        #change mixin
        role_d, role_e = self.env['planning.role'].create([
            {'name': 'role d'},
            {'name': 'role e'},
        ])
        roles |= role_d
        roles = roles - role_a

        self.employee_joseph.write({'planning_role_ids': roles, 'default_planning_role_id': role_e})
        roles |= role_e

        self.assertEqual(self.employee_joseph.resource_id.role_ids, roles, "Joseph should have role b, c, d and e as roles")
        self.assertEqual(self.employee_joseph.default_planning_role_id, role_e, "Joseph should have role e as default role")
        self.assertEqual(self.employee_joseph.planning_role_ids, roles, "Joseph should have role b, c, d and e as resource_id.role_ids")

    def test_hr_employee_view_planning(self):
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2021, 6, 4, 8, 0),
            'end_datetime': datetime(2021, 6, 5, 17, 0),
        }).copy()
        action = self.employee_bert.action_view_planning()
        # just returns action
        slots = self.env['planning.slot'].search(action['domain'])
        self.assertEqual(action['res_model'], 'planning.slot')
        self.assertEqual(len(slots), 2, 'Bert has 2 planning slots')
        self.assertEqual(action['context']['default_resource_id'], self.resource_bert.id)

    def test_employee_contract_validity_per_period(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=pytz.UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=pytz.UTC)
        calendars_validity_within_period = self.employee_joseph.resource_id._get_calendars_validity_within_period(start, end, default_company=self.employee_joseph.company_id)

        self.assertEqual(len(calendars_validity_within_period[self.employee_joseph.resource_id.id]), 1, "There should exist 1 calendar within the period")
        interval_calendar_joseph = Intervals([(
            start,
            end,
            self.env['resource.calendar.attendance']
        )])
        computed_interval = calendars_validity_within_period[self.employee_joseph.resource_id.id][self.employee_joseph.resource_calendar_id]
        self.assertFalse(computed_interval - interval_calendar_joseph, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not more")
        self.assertFalse(interval_calendar_joseph - computed_interval, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not less")

    def test_employee_work_intervals(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=pytz.UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=pytz.UTC)
        work_intervals, _ = self.employee_joseph.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum(
            (stop - start).total_seconds() / 3600
            for start, stop, _resource in work_intervals[self.employee_joseph.resource_id.id]
        )
        self.assertEqual(16, sum_work_intervals, "Sum of the work intervals for the employee Joseph should be 8h+8h = 16h")

    def test_employee_work_planning_hours_info(self):
        joseph_resource_id = self.employee_joseph.resource_id
        self.env['planning.slot'].create([{
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 8, 8, 0),
            'end_datetime': datetime(2015, 11, 14, 17, 0),
            # allocated_hours will be : 8h (see calendar)
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 16, 8, 0),
            'end_datetime': datetime(2015, 11, 16, 17, 0),
            # allocated_hours will be : 0h (see calendar)
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 17, 8, 0),
            'end_datetime': datetime(2015, 11, 17, 17, 0),
            # allocated_hours will be : 0h (see calendar)
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 18, 8, 0),
            'end_datetime': datetime(2015, 11, 18, 17, 0),
            # allocated_hours will be : 0h (see calendar)
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 23, 8, 0),
            'end_datetime': datetime(2015, 11, 27, 17, 0),
            'allocated_percentage': 50.0,
            # allocated_hours will be : 4h (see calendar)
        }])

        planning_hours_info = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', joseph_resource_id.ids, datetime(2015, 11, 8), datetime(2015, 11, 28, 23, 59, 59)
        )
        self.assertEqual(24, planning_hours_info[joseph_resource_id.id]['max_value'], "Work hours for the employee Jules should be 8h+8h+8h = 24h")
        self.assertEqual(12, planning_hours_info[joseph_resource_id.id]['value'], "Planned hours for the employee Jules should be 8h+4h = 12h")

        planning_hours_info = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', joseph_resource_id.ids, datetime(2015, 11, 12), datetime(2015, 11, 12, 23, 59, 59)
        )
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['max_value'],
                         "Work hours for the employee Jules should be 8h as its a Thursday.")
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['value'],
                         "Planned hours for the employee Jules should be 8h as its a Thursday and hours are computed on a forecast slot.")

        planning_hours_info = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', joseph_resource_id.ids, datetime(2015, 11, 26), datetime(2015, 11, 26, 23, 59, 59)
        )
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['max_value'],
                         "Work hours for the employee Jules should be 8h as its a Thursday.")
        self.assertEqual(4, planning_hours_info[joseph_resource_id.id]['value'],
                         "Planned hours for the employee Jules should be 4h as its a Thursday and hours are computed on a forecast slot (allocated_percentage = 50).")
