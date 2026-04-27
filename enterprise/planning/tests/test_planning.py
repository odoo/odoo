# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
import re
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from odoo.exceptions import UserError

from odoo import fields
from odoo.tests import Form, new_test_user

from odoo.addons.mail.tests.common import MockEmail
from .common import TestCommonPlanning

class TestPlanning(TestCommonPlanning, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.datetime.now)
        with freeze_time('2019-5-1'):
            cls.setUpCalendars()
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
        calendar_bert = cls.env['resource.calendar'].create({
            'name': 'Calendar 2',
            'tz': 'UTC',
            'hours_per_day': 4,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'morning'}),
            ],
        })
        cls.env.user.company_id.resource_calendar_id = cls.company_calendar
        cls.employee_joseph.resource_calendar_id = calendar_joseph
        cls.employee_bert.resource_calendar_id = calendar_bert
        cls.slot, cls.slot2 = cls.env['planning.slot'].create([
            {
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 27, 18, 0, 0),
            },
            {
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 28, 18, 0, 0),
            }
        ])
        cls.template = cls.env['planning.slot.template'].create({
            'start_time': 11,
            'end_time': 14,
            'duration_days': 1,
        })

    def test_allocated_hours_defaults(self):
        self.assertEqual(self.slot.allocated_hours, 8, "It should follow the calendar of the resource to compute the allocated hours.")
        self.assertEqual(self.slot.allocated_percentage, 100, "It should have the default value")

    def test_change_percentage(self):
        self.slot.allocated_percentage = 60
        self.assertEqual(self.slot.allocated_hours, 8 * 0.60, "It should 60%% of working hours")
        self.slot2.allocated_percentage = 60
        self.assertEqual(self.slot2.allocated_hours, 16 * 0.60)

    def test_change_hours_more(self):
        self.slot.allocated_hours = 12
        self.assertEqual(self.slot.allocated_percentage, 150)
        self.slot2.allocated_hours = 24
        self.assertEqual(self.slot2.allocated_percentage, 150)

    def test_change_hours_less(self):
        self.slot.allocated_hours = 4
        self.assertEqual(self.slot.allocated_percentage, 50)
        self.slot2.allocated_hours = 8
        self.assertEqual(self.slot2.allocated_percentage, 50)

    def test_change_start(self):
        self.slot.start_datetime += relativedelta(hours=2)
        self.assertEqual(self.slot.allocated_percentage, 100, "It should still be 100%")
        self.assertEqual(self.slot.allocated_hours, 8, "It should decreased by 2 hours")

    def test_change_start_partial(self):
        self.slot.allocated_percentage = 80
        self.slot.start_datetime += relativedelta(hours=2)
        self.slot.flush_recordset()
        self.slot.invalidate_recordset()
        self.assertEqual(self.slot.allocated_hours, 8 * 0.8, "It should be decreased by 2 hours and percentage applied")
        self.assertEqual(self.slot.allocated_percentage, 80, "It should still be 80%")

    def test_change_end(self):
        self.slot.end_datetime -= relativedelta(hours=2)
        self.assertEqual(self.slot.allocated_percentage, 100, "It should still be 100%")
        self.assertEqual(self.slot.allocated_hours, 8, "It should decreased by 2 hours")

    def test_set_template(self):
        self.env.user.tz = 'Europe/Brussels'
        self.slot.template_id = self.template
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 9, 0), 'It should set time from template, in user timezone (11am CET -> 9am UTC)')

    def test_change_employee_with_template(self):
        self.env.user.tz = 'UTC'
        self.slot.template_id = self.template
        self.env.flush_all()

        # simulate public user (no tz)
        self.env.user.tz = False
        self.slot.resource_id = self.employee_janice.resource_id
        self.assertEqual(self.slot.template_id, self.template, 'It should keep the template')
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should adjust for employee timezone: 11am EDT -> 3pm UTC')

    def test_change_employee(self):
        """ Ensures that changing the employee does not have an impact to the shift. """
        self.env.user.tz = 'UTC'
        self.slot.resource_id = self.employee_joseph.resource_id
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 8, 0), 'It should not adjust to employee calendar')
        self.assertEqual(self.slot.end_datetime, datetime(2019, 6, 27, 18, 0), 'It should not adjust to employee calendar')
        self.slot.resource_id = self.employee_bert.resource_id
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 8, 0), 'It should not adjust to employee calendar')
        self.assertEqual(self.slot.end_datetime, datetime(2019, 6, 27, 18, 0), 'It should not adjust to employee calendar')

    def test_create_with_employee(self):
        """ This test's objective is to mimic shift creation from the gant view and ensure that the correct behavior is met.
            This test objective is to test the default values when creating a new shift for an employee when provided defaults are within employee's calendar workdays
        """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-27 00:00:00',
            default_end_datetime='2019-06-27 23:59:59',
            default_resource_id=self.resource_joseph.id)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 27, 9, 0), 'It should be adjusted to employee calendar: 0am -> 9pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 27, 18, 0), 'It should be adjusted to employee calendar: 0am -> 18pm')

    def test_specific_time_creation(self):
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2020-10-05 06:00:00',
            default_end_datetime='2020-10-05 12:30:00',
            planning_keep_default_datetime=True)
        defaults = PlanningSlot.default_get(['start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2020, 10, 5, 6, 0), 'start_datetime should not change')
        self.assertEqual(defaults.get('end_datetime'), datetime(2020, 10, 5, 12, 30), 'end_datetime should not change')

    def test_create_with_employee_outside_schedule(self):
        """ This test objective is to test the default values when creating a new shift for an employee when provided defaults are not within employee's calendar workdays """
        self.env.user.tz = 'UTC'
        # Case 1: Create a planning slot on non-working days with a specific employee resource
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-26 00:00:00',
            default_end_datetime='2019-06-26 23:59:59',
            default_resource_id=self.resource_joseph.id)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 26, 8, 0), 'It should adjust to employee calendar: 0am -> 8pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 26, 17, 0), 'It should adjust to employee calendar: 0am -> 5am')

        # Case 2: Create a planning slot on non-working days without a specific employee resource
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-12-07 00:00:00',
            default_end_datetime='2019-12-08 23:59:59',
        )
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])

        self.assertEqual(
            defaults.get('start_datetime'),
            datetime(2019, 12, 7, 8, 0),
            'The start time should be adjusted to the default working hours: 8:00 AM on non-working days'
        )
        self.assertEqual(
            defaults.get('end_datetime'),
            datetime(2019, 12, 8, 17, 0),
            'The end date should be adjusted to the default working hours: 17:00 on on non-working days'
        )

    def test_create_without_employee(self):
        """ This test objective is to test the default values when creating a new shift when no employee is set """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-27 00:00:00',
            default_end_datetime='2019-06-27 23:59:59',
            default_resource_id=False)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 27, 6, 0), 'It should adjust to employee calendar: 0am -> 6pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 27, 15, 0), 'It should adjust to employee calendar: 0am -> 3pm')

    def test_unassign_employee_with_template(self):
        # we are going to put everybody in EDT, because if the employee has a different timezone from the company this workflow does not work.
        self.env.user.tz = 'America/New_York'
        self.env.user.company_id.resource_calendar_id.tz = 'America/New_York'
        self.slot.template_id = self.template
        self.env.flush_all()
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should set time from template, in user timezone (11am EDT -> 3pm UTC)')

        # simulate public user (no tz)
        self.env.user.tz = False
        self.slot.resource_id = self.resource_janice.id
        self.env.flush_all()
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should adjust to employee timezone')

        self.slot.resource_id = None
        self.assertEqual(self.slot.template_id, self.template, 'It should keep the template')
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should reset to company calendar timezone: 11am EDT -> 3pm UTC')

    def test_compute_overlap_count(self):
        self.slot_6_2 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 8, 0),
            'end_datetime': datetime(2019, 6, 2, 17, 0),
        })
        self.slot_6_3 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),
            'end_datetime': datetime(2019, 6, 3, 17, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 10, 0),
            'end_datetime': datetime(2019, 6, 2, 12, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 16, 0),
            'end_datetime': datetime(2019, 6, 2, 18, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 18, 0),
            'end_datetime': datetime(2019, 6, 2, 20, 0),
        })
        self.assertEqual(2, self.slot_6_2.overlap_slot_count, '2 slots overlap')
        self.assertEqual(0, self.slot_6_3.overlap_slot_count, 'no slot overlap')

    def test_compute_datetime_with_template_slot(self):
        """ Test if the start and end datetimes of a planning.slot are correctly computed with the template slot

            Test Case:
            =========
            1) Create a planning.slot.template with start_hours = 11 am, end_hours = 2pm and duration_days = 2.
            2) Create a planning.slot for one day and add the template.
            3) Check if the start and end dates are on two days and not one.
            4) Check if the allocating hours is equal to the working hours of the resource.
        """
        self.employee_bert.resource_calendar_id = self.company_calendar
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 11,
            'end_time': 14,
            'duration_days': 2,
        })

        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 4, 0, 0),
            'end_datetime': datetime(2021, 1, 4, 23, 59),
            'resource_id': self.resource_bert.id,
        })

        slot.write({
            'template_id': template_slot.id,
        })

        self.assertEqual(slot.start_datetime, datetime(2021, 1, 4, 11, 0), 'The start datetime should have the same hour and minutes defined in the template in the resource timezone.')
        self.assertEqual(slot.end_datetime, datetime(2021, 1, 5, 14, 0), 'The end datetime of this slot should be 3 hours after the start datetime as mentionned in the template in the resource timezone.')
        self.assertEqual(slot.allocated_hours, 10, 'The allocated hours of this slot should be the duration defined in the template in the resource timezone.')

    def test_planning_state(self):
        """ The purpose of this test case is to check the planning state """
        self.slot.resource_id = self.employee_bert.resource_id
        self.assertEqual(self.slot.state, 'draft', 'Planning is draft mode.')
        self.slot.action_send()
        self.assertEqual(self.slot.state, 'published', 'Planning is published.')

    def test_create_working_calendar_period(self):
        """ A default dates should be calculated based on the working calendar of the company whatever the period """
        test = Form(self.env['planning.slot'].with_context(
            default_start_datetime=datetime(2019, 5, 27, 0, 0),
            default_end_datetime=datetime(2019, 5, 27, 23, 59, 59)
        ))
        slot = test.save()
        self.assertEqual(slot.start_datetime, datetime(2019, 5, 27, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(slot.end_datetime, datetime(2019, 5, 27, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')

        # For weeks period
        test_week = Form(self.env['planning.slot'].with_context(
            default_start_datetime=datetime(2019, 6, 23, 0, 0),
            default_end_datetime=datetime(2019, 6, 29, 23, 59, 59)
        ))

        test_week = test_week.save()
        self.assertEqual(test_week.start_datetime, datetime(2019, 6, 24, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(test_week.end_datetime, datetime(2019, 6, 28, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')

    def test_create_planing_slot_without_start_date(self):
        "Test to create planning slot with template id and without start date"
        planning_role = self.env['planning.role'].create({'name': 'role x'})
        template = self.env['planning.slot.template'].create({
            'start_time': 10,
            'end_time': 15,
            'duration_days': 1,
            'role_id': planning_role.id,
        })
        with Form(self.env['planning.slot']) as slot_form:
            slot_form.template_id = template
            slot_form.start_datetime = False
            slot_form.template_id = self.template
            self.assertEqual(slot_form.template_id, self.template)

    def test_shift_switching(self):
        """ The purpose of this test is to check the main back-end mechanism of switching shifts between employees """
        bert_user = new_test_user(self.env,
                                  login='bert_user',
                                  groups='planning.group_planning_user',
                                  name='Bert User',
                                  email='user@example.com')
        self.employee_bert.user_id = bert_user.id
        joseph_user = new_test_user(self.env,
                                    login='joseph_user',
                                    groups='planning.group_planning_user',
                                    name='Joseph User',
                                    email='juser@example.com')
        self.employee_joseph.user_id = joseph_user.id

        # Lets first try to switch a shift that is in the past - should throw an error
        self.slot.resource_id = self.employee_bert.resource_id
        self.assertEqual(self.slot.is_past, True, 'The shift for this test should be in the past')
        with self.assertRaises(UserError):
            self.slot.with_user(bert_user).action_switch_shift()

        # Lets now try to switch a shift that is not ours - it should again throw an error
        self.assertEqual(self.slot.resource_id, self.employee_bert.resource_id, 'The shift should be assigned to Bert')
        with self.assertRaises(UserError):
            self.slot.with_user(joseph_user).action_switch_shift()

        # Lets now to try to switch a shift that is both in the future and is ours - this should not throw an error
        test_slot = self.env['planning.slot'].create({
            'start_datetime': datetime.now() + relativedelta(days=2),
            'end_datetime': datetime.now() + relativedelta(days=4),
            'state': 'published',
            'employee_id': bert_user.employee_id.id,
            'resource_id': self.employee_bert.resource_id.id,
        })

        with self.mock_mail_gateway():
            self.assertEqual(test_slot.request_to_switch, False, 'Before requesting to switch, the request to switch should be False')
            test_slot.with_user(bert_user).action_switch_shift()
            self.assertEqual(test_slot.request_to_switch, True, 'After the switch action, the request to switch should be True')

            # Lets now assign another user to the shift - this should remove the request to switch and assign the shift
            test_slot.with_user(joseph_user).action_self_assign()
            self.assertEqual(test_slot.request_to_switch, False, 'After the assign action, the request to switch should be False')
            self.assertEqual(test_slot.resource_id, self.employee_joseph.resource_id, 'The shift should now be assigned to Joseph')

            # Lets now create a new request and then change the start datetime of the switch - this should remove the request to switch
            test_slot.with_user(joseph_user).action_switch_shift()
            self.assertEqual(test_slot.request_to_switch, True, 'After the switch action, the request to switch should be True')
            test_slot.write({'start_datetime': (datetime.now() + relativedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")})
            self.assertEqual(test_slot.request_to_switch, False, 'After the change, the request to switch should be False')

        self.assertEqual(len(self._new_mails), 1)
        self.assertMailMailWEmails(
            [bert_user.partner_id.email],
            None,
            author=joseph_user.partner_id,
        )

    @freeze_time("2023-11-20")
    def test_shift_creation_from_role(self):
        self.env.user.tz = 'Asia/Kolkata'
        self.env.user.company_id.resource_calendar_id.tz = 'Asia/Kolkata'
        PlanningRole = self.env['planning.role']
        PlanningTemplate = self.env['planning.slot.template']

        role_a = PlanningRole.create({'name': 'role a'})
        role_b = PlanningRole.create({'name': 'role b'})

        template_a = PlanningTemplate.create({
            'start_time': 8,
            'end_time': 10,
            'duration_days': 1,
            'role_id': role_a.id
        })
        self.assertEqual(template_a.duration_days, 1, "Duration in days should be a 1 day according to resource calendar.")
        self.assertEqual(template_a.end_time, 10.0, "End time should be 2 hours from start hours.")

        template_b = PlanningTemplate.create({
            'start_time': 8,
            'end_time': 12,
            'duration_days': 1,
            'role_id': role_b.id
        })

        slot = self.env['planning.slot'].create({'template_id': template_a.id})
        self.assertEqual(slot.role_id.id, slot.template_autocomplete_ids.mapped('role_id').id, "Role of the slot and shift template should be same.")

        slot.template_id = template_b.id
        self.assertEqual(slot.role_id.id, slot.template_autocomplete_ids.mapped('role_id').id, "Role of the slot and shift template should be same.")

    def test_manage_archived_resources(self):
        with freeze_time("2020-04-22"):
            self.env.user.tz = 'UTC'
            slot_1, slot_2, slot_3 = self.env['planning.slot'].create([
                {
                    'resource_id': self.resource_bert.id,
                    'start_datetime': datetime(2020, 4, 20, 8, 0),
                    'end_datetime': datetime(2020, 4, 24, 17, 0),
                },
                {
                    'resource_id': self.resource_bert.id,
                    'start_datetime': datetime(2020, 4, 20, 8, 0),
                    'end_datetime': datetime(2020, 4, 21, 17, 0),
                },
                {
                    'resource_id': self.resource_bert.id,
                    'start_datetime': datetime(2020, 4, 23, 8, 0),
                    'end_datetime': datetime(2020, 4, 24, 17, 0),
                },
            ])

            slot1_initial_end_date = slot_1.end_datetime
            slot2_initial_end_date = slot_2.end_datetime

            self.resource_bert.employee_id.action_archive()

            self.assertEqual(slot_1.end_datetime, datetime.combine(fields.Date.today()+ timedelta(days=1), time.min), 'End date of the splited shift should be today')
            self.assertNotEqual(slot_1.end_datetime, slot1_initial_end_date, 'End date should be updated')
            self.assertEqual(slot_2.end_datetime, slot2_initial_end_date, 'End date should be the same')
            self.assertFalse(slot_3.resource_id, 'Resource should be the False for archeived resource shifts')

    def test_avoid_rounding_error_when_creating_template(self):
        """
        Regression test: in some odd circumstances,
        a floating point error during the divmod conversion from float -> hours/min can lead to incorrect minutes
        5.1 after a divmod(1) gives back minutes = 0.0999999999964 instead of 1, hence the source of error
        """
        template = self.env['planning.slot.template'].create({
            'start_time': 8,
            'end_time': 13.1,
            'duration_days': 1,
        })
        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 1, 0, 0),
            'end_datetime': datetime(2021, 1, 1, 23, 59),
        })
        slot.write({
            'template_id': template.id,
        })
        self.assertEqual(slot.end_datetime.minute, 6, 'The min should be 6, just like in the template, not 5 due to rounding error')

    def test_end_time_rounding_edge_case(self):
        """
        Test to ensure 0.996 doesn't round to 60,
        minutes need to be between 0 and 59.
        """
        shift_template = self.env['planning.slot.template'].create({
            'start_time': 8.995,
            'end_time': 17.996,
            'duration_days': 1,
        })
        self.assertEqual(re.sub(r'\s+', ' ', shift_template.name).strip(), '8:59 AM - 5:59 PM')

    def test_copy_planning_shift(self):
        """ Test state of the planning shift is only copied once we are in the planning split tool

            Test Case:
            =========
            1) Create a planning shift with state published.
            2) Copy the planning shift as we are in the planning split tool (planning_split_tool=True in the context).
            3) Check the state of the new planning shift is published.
            4) Copy the planning shift as we are not in the planning split tool (planning_split_tool=False in the context).
            5) Check the state of the new planning shift is draft.
            6) Copy the planning shift without the context (= diplicate a shift).
            7) Check the state of the new planning shift is draft.
        """
        self.env.user.tz = 'UTC'
        slot = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2020, 4, 20, 8, 0),
            'end_datetime': datetime(2020, 4, 24, 17, 0),
            'state': 'published',
        })
        self.assertEqual(slot.state, 'published', 'The state of the shift should be published')

        slot1 = slot.with_context(planning_split_tool=True).copy()
        self.assertEqual(slot1.state, 'published', 'The state of the shift should be copied')

        slot2 = slot.with_context(planning_split_tool=False).copy()
        self.assertEqual(slot2.state, 'draft', 'The state of the shift should not be copied')

        slot3 = slot.copy()
        self.assertEqual(slot3.state, 'draft', 'The state of the shift should not be copied')

    def test_calculate_slot_duration_flexible_hours(self):
        """ Ensures that _calculate_slot_duration function rounds up days only when there is an extra non-full day left """

        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
        })
        employee.resource_id.calendar_id = self.flex_40h_calendar

        # the diff between start and end is exactly 6 days
        planning_slot_1 = self.env['planning.slot'].create({
            'resource_id': employee.resource_id.id,
            'start_datetime': datetime(2024, 2, 23, 6, 0, 0),
            'end_datetime': datetime(2024, 2, 29, 6, 0, 0),
        })
        self.assertEqual(planning_slot_1.allocated_hours, 48.0)

        # the diff between start and end is 6 days and 8 hours, hence the diff should be approximated to 7 days
        planning_slot_2 = self.env['planning.slot'].create({
            'resource_id': employee.resource_id.id,
            'start_datetime': datetime(2024, 2, 23, 8, 0, 0),
            'end_datetime': datetime(2024, 2, 29, 16, 0, 0),
        })
        self.assertEqual(planning_slot_2.allocated_hours, 56.0)

    def test_auto_plan_employee_with_break_company_no_breaks(self):
        """ Test auto-planning an employee with break, while company calendar without breaks

            Test Case:
            =========
            1) Create company calendar with 24 hours per day.
            2) Create employee with night shifts calendar, with 30 minutes break at midnight.
            3) Create shift from 21:30 to 6:00 with 8 allocated hours.
            4) Auto-plan the shift.
            5) Check the shift is assigned to the employee.
            6) Check the allocated hours remain the same.
        """
        # Create a 24-hour company calendar
        calendar_24hr = self.env['resource.calendar'].create({
            'name': '24/24 Company Calendar',
            'tz': 'UTC',
            'hours_per_day': 24.0,
            'attendance_ids': [
                (0, 0, {'name': 'Morning ' + str(day), 'dayofweek': str(day), 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'})
                for day in range(7)
            ] + [
                (0, 0, {'name': 'Afternoon ' + str(day), 'dayofweek': str(day), 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'})
                for day in range(7)
            ],
        })
        self.env.user.company_id.resource_calendar_id = calendar_24hr

        night_shifts_calendar = self.env['resource.calendar'].create({
            'name': 'Night Shifts Calendar',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Afternoon ' + str(day), 'dayofweek': str(day), 'hour_from': 21.5, 'hour_to': 24, 'day_period': 'afternoon'})
                for day in range(7)
            ] + [
                (0, 0, {'name': 'Break ' + str(day), 'dayofweek': str(day), 'hour_from': 0, 'hour_to': 0.5, 'day_period': 'lunch'})
                for day in range(7)
            ] + [
                (0, 0, {'name': 'morning ' + str(day), 'dayofweek': str(day), 'hour_from': 0.5, 'hour_to': 6, 'day_period': 'morning'})
                for day in range(7)
            ],
        })
        role = self.env['planning.role'].create({'name': 'test role'})
        # Create an employee linked to this calendar
        night_employee = self.env['hr.employee'].create({
            'name': 'Night employee',
            'resource_calendar_id': night_shifts_calendar.id,
            'default_planning_role_id': role.id,
        })

        # Create a shift from 21:30 to 6:00 with an allocated 8 hours
        night_shift = self.env['planning.slot'].create({
            'name': 'Night Shift',
            'start_datetime': datetime(2024, 5, 10, 21, 30),
            'end_datetime': datetime(2024, 5, 11, 6, 0),
            'role_id': role.id,
        })
        night_shift.allocated_hours = 8
        # Execute auto-plan to assign the employee
        night_shift.auto_plan_id()

        self.assertEqual(night_shift.resource_id, night_employee.resource_id, 'The night shift should be assigned to the night employee')
        self.assertEqual(night_shift.allocated_hours, 8, 'The allocated hours should remain the same')
        self.assertEqual(night_shift.allocated_percentage, 100, 'The allocated percentage should be 100% as the resource will work the allocated hours')

    def test_write_multiple_slots(self):
        """ Test that we can write a resource_id on multiple slots at once. """
        slots = self.env['planning.slot'].create([
            {'start_datetime': datetime(2024, 5, 10, 8, 0), 'end_datetime': datetime(2024, 5, 10, 17, 0)},
            {'start_datetime': datetime(2024, 6, 10, 8, 0), 'end_datetime': datetime(2024, 6, 10, 17, 0)},
        ])
        slots.write({'resource_id': self.resource_bert.id})
        self.assertEqual(slots.resource_id, self.resource_bert)

    def test_write_without_resource(self):
        slot = self.env['planning.slot'].create(
            {'start_datetime': datetime(2024, 5, 10, 8, 0), 'end_datetime': datetime(2024, 5, 10, 17, 0)}
        )
        slot.write({
            'repeat' : True,
            'recurrence_update': 'all',
            'start_datetime': datetime(2024, 5, 10, 9, 0),
            'end_datetime': datetime(2024, 5, 10, 18, 0),
        })
        self.assertRecordValues(slot, [{
            'repeat': True,
            'start_datetime': datetime(2024, 5, 10, 9, 0),
            'end_datetime': datetime(2024, 5, 10, 18, 0),
        }])

    def test_compute_company_planning_slot(self):
        self.assertEqual(self.slot.company_id, self.env.company, "The slot's company should be the current one.")
        company = self.env['res.company'].create({"name": "Test company"})
        self.resource_bert.company_id = company.id
        self.slot.resource_id = self.resource_bert.id
        self.assertEqual(self.slot.company_id, company, "The slot's company should be the resource's one.")

    def test_flexible_contract_slot(self):
        """
            A flexible contract should have no constraints on the slots in terms of start/end time,
            but the duration cannot exceed the hours_per_day defined in the contract.
        """
        # Create a shift longer than the calendar's hours_per_day
        self.employee_bert.resource_calendar_id = self.flex_50h_calendar
        slot = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2022, 1, 11, 3, 0),
            'end_datetime': datetime(2022, 1, 11, 23, 0),
            'state': 'published',
        })
        self.assertEqual(slot.allocated_hours, 10.0, 'The allocated hours should be 10.0')
        self.assertEqual(slot.allocated_percentage, 100, 'The allocated percentage should be 100%%')

        # Create a night shift that spans over two days, but shorter than the calendar's hours_per_day
        slot = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2022, 1, 12, 22, 0),
            'end_datetime': datetime(2022, 1, 13, 4, 0),
            'state': 'published',
        })
        self.assertEqual(slot.allocated_hours, 6.0, 'The allocated hours should be 6.0')
        self.assertEqual(slot.allocated_percentage, 100, 'The allocated percentage should be 100%%')

        # Create a night shift that spans over two days and is longer than the calendar's hours_per_day
        slot = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2022, 1, 13, 20, 0),
            'end_datetime': datetime(2022, 1, 14, 10, 0),
            'state': 'published',
        })
        self.assertEqual(slot.allocated_hours, 10.0, 'The allocated hours should be limited to 10.0')
        self.assertEqual(slot.allocated_percentage, 100, 'The allocated percentage should be 100%%')

        # Changing the allocated time percentage should be reflected in the allocated hours
        slot.allocated_percentage = 50
        self.assertEqual(slot.allocated_hours, 5.0, 'The allocated hours should be 5.0 after changing the allocated percentage to 50%%')

    def test_fully_flexible_contract_slot(self):
        """
            A fully flexible contract should not have any constraints on the slots in terms of duration and start time.
        """
        self.employee_bert.resource_calendar_id = False
        slot = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2022, 1, 11, 4, 0),
            'end_datetime': datetime(2022, 1, 12, 22, 0),
            'state': 'published',
        })
        self.assertEqual(slot.allocated_hours, 42.0, 'The allocated hours should be 42.0')
        self.assertEqual(slot.allocated_percentage, 100, 'The allocated percentage should be 100%%')

        # Changing the allocated time percentage should be reflected in the allocated hours
        slot.allocated_percentage = 50
        self.assertEqual(slot.allocated_hours, 21.0, 'The allocated hours should be 21.0 after changing the allocated percentage to 50%%')

    def test_open_shift_planning_slot_including_weekend(self):
        """
            When an open shift is scheduled spanning between weekday and weekends (e.g. Sunday 8 AM to Monday 5 PM),
            allocated time should be equal to 16h instead of 8h (same behavior as for employees working flexible hours):
        """
        slot = self.env['planning.slot'].create({
            'resource_id': False,
            'start_datetime': datetime(2022, 1, 16, 8, 0),  # Sunday 8AM
            'end_datetime': datetime(2022, 1, 17, 17, 0),   # Monday 5PM
            'state': 'published',
        })
        self.assertEqual(slot.allocated_hours, 16.0, 'The allocated hours should be 16.0 for the open shift')
        self.assertEqual(slot.allocated_percentage, 100, 'The allocated percentage should be 100%%')

    def test_auto_plan_should_ignore_resource_with_flexible_hours(self):
        """
            When auto-planning a shift, the system should ignore resources with flexible hours.

            Test Case:
            =========
            1) Create a role `night_shift_role` to exclude all other resources.
            2) Create two employees with flexible calendars, and planning role set to `night_shift_role`.
            3) Create a night shift from 21:30 to 6:00 with 8 allocated hours, and auto-plan the shift.
            4) Check the shift is not assigned to these employees with flexible hours.
            5) Create a employee with night shifts calendar, and planning role set to `night_shift_role`.
            6) The new employee should be assigned to the shift when we re-run the auto-plan.
        """
        # create role
        night_shift_role = self.env['planning.role'].create({'name': 'flex_shift'})

        # set the calendar for the employee as flexible, and set the role
        self.employee_bert.resource_calendar_id = False
        self.employee_joseph.resource_calendar_id = self.flex_40h_calendar

        self.employee_bert.planning_role_ids = night_shift_role
        self.employee_joseph.planning_role_ids = night_shift_role

        # Create a shift from 21:30 to 6:00 with an allocated 8 hours
        night_shift = self.env['planning.slot'].create({
            'name': 'Night Shift',
            'start_datetime': datetime(2024, 5, 10, 21, 30),
            'end_datetime': datetime(2024, 5, 11, 6, 0),
            'role_id': night_shift_role.id,
        })
        night_shift.allocated_hours = 8

        # Execute auto-plan to assign the employee
        night_shift.auto_plan_id()
        self.assertFalse(night_shift.resource_id, 'The auto plan should not assign employees with flexible hours')

        # Create a night shifts calendar with 8 hours per day
        night_shifts_calendar = self.env['resource.calendar'].create({
            'name': 'Night Shifts Calendar',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Afternoon ' + str(day), 'dayofweek': str(day), 'hour_from': 21.5, 'hour_to': 24, 'day_period': 'afternoon'})
                for day in range(7)
            ] + [
                (0, 0, {'name': 'Break ' + str(day), 'dayofweek': str(day), 'hour_from': 0, 'hour_to': 0.5, 'day_period': 'lunch'})
                for day in range(7)
            ] + [
                (0, 0, {'name': 'morning ' + str(day), 'dayofweek': str(day), 'hour_from': 0.5, 'hour_to': 6, 'day_period': 'morning'})
                for day in range(7)
            ],
        })
        # Create an employee linked to this calendar
        night_employee = self.env['hr.employee'].create({
            'name': 'Night employee',
            'resource_calendar_id': night_shifts_calendar.id,
            'planning_role_ids': night_shift_role,
        })

        # this time it should select the night_employee who's calendar is not flexible
        night_shift.auto_plan_id()
        self.assertEqual(night_shift.resource_id, night_employee.resource_id, 'The auto plan should assign the shift to the night employee')

    @freeze_time('2021-01-01')
    def test_allocated_hours_when_template_is_during_a_break(self):
        self.resource_janice.tz = 'UTC'
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 11,
            'end_time': 16,
        })

        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 1, 0, 0),
            'end_datetime': datetime(2021, 1, 1, 23, 59),
            'resource_id': self.resource_janice.id,
        })

        slot.write({
            'template_id': template_slot.id,
        })

        self.assertEqual(slot.start_datetime, datetime(2021, 1, 1, 11, 0))
        self.assertEqual(slot.end_datetime, datetime(2021, 1, 1, 16, 0))
        self.assertEqual(slot.allocated_hours, 4)

    def test_allocated_hours_shift_duplication(self):
        self.slot.resource_id = self.resource_joseph
        self.assertEqual(self.slot.allocated_hours, 8)
        slot2 = self.slot.copy({'resource_id': self.resource_bert.id})
        self.assertEqual(slot2.allocated_hours, 4, "The allocated hours should have been recomputed with the new resource after copying the shift.")

    def test_planning_slot_default_datetime(self):
        """ This test ensures that when selecting the datetime in Gantt view, the default hours are set correctly """
        self.resource_joseph.tz = 'Europe/Brussels'
        PlanningSlot = self.env['planning.slot'].with_user(self.env.user).with_context(
            default_start_datetime='2024-07-04 12:00:00',
            default_end_datetime='2024-07-04 12:59:59',
            default_resource_id=self.resource_joseph.id,
        )
        slot = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(slot.get('start_datetime'), datetime(2024, 7, 4, 10, 0, 0), "The slot start datetime should be matched to the resource's timezone")
        self.assertEqual(slot.get('end_datetime'), datetime(2024, 7, 4, 10, 59, 59), "The slot end datetime should be matched to the resource's timezone")

    def test_copy_slots_when_time_off(self):
        """
        week_1: 19-01-2020 -> 25-01-2020
            original slot: 20-01-2020 08:00 -> 24-01-2020 17:00 (5 days)
            allocated_hours: 50 hours and allocated_percentage: 125
        --------------------------------------------------------------------------------------------
        week_2: 26-01-2020 -> 01-02-2020
            resource on leave: 28-01-2020 8:00 -> 29-01-2020 17:00 (2 days i.e 16 hours)
            copy slot: 27-01-2020 08:00 -> 31-01-2020 17:00
        -------------------------------------------------------------------------------------------
        Expected result:
        Total 4 slots will create, 3 slot assigned to resource and 1 open slot
            1) 27-01-2020 08:00 -> 27-01-2020 12:00 (4 hrs)(assigned slot)
            2) 27-01-2020 13:00 -> 27-01-2020 19:00 (4 hrs)(assigned slot)
            3) 28-01-2020 08:00 -> 29-01-2020 19:00 (16 hrs)(open slot)
            4) 30-01-2020 08:00 -> 31-01-2020 19:00 (16 hrs)(assigned slot)
        """
        employee_bert = self.employee_bert.copy()
        employee_bert.resource_calendar_id = self.company_calendar.id

        PlanningSlot = self.env['planning.slot']
        dt = datetime(2020, 1, 20, 0, 0)

        slot = PlanningSlot.create({
            'resource_id': employee_bert.resource_id.id,
            'start_datetime': dt + relativedelta(hours=8),
            'end_datetime': dt + relativedelta(days=4, hours=17),
        })

        self.env['resource.calendar.leaves'].create({
            'name': "I go to my father-in-law's",
            'calendar_id': employee_bert.resource_id.calendar_id.id,
            'date_from': dt + relativedelta(weeks=1, days=1),
            'date_to': dt + relativedelta(weeks=1, days=2, hours=17),
            'resource_id': employee_bert.resource_id.id,
        })

        copied, _dummy = PlanningSlot.action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', employee_bert.resource_id.id],
            ]
        )

        copied_slot = PlanningSlot.browse(copied)
        open_slot = copied_slot.filtered(lambda x: not x.resource_id)

        self.assertEqual(len(open_slot), 4, "4 shift should be copied as open, as the employee is on off")
        self.assertEqual(sum(open_slot.mapped('allocated_hours')), 16, "16 hours should be allocated to open slot")
        self.assertEqual(slot.allocated_hours, sum(copied_slot.mapped('allocated_hours')),
            "The allocated hours of slot and allocated hours of copied slots must be same")

    def test_gantt_progress_bar_split_when_flexible(self):
        """
        Test if a slot is shared between two weeks the progress bar
        should be split between both weeks. Not showing the whole allocated
        hours in both weeks.
        """
        self.employee_bert.resource_calendar_id = self.flex_40h_calendar.id

        dt = datetime(2025, 8, 22, 0, 0)

        self.slot.write({
            'resource_id': self.employee_bert.resource_id.id,
            'start_datetime': dt + relativedelta(hours=8),
            'end_datetime': dt + relativedelta(days=4, hours=17),
        })

        planning_hours_info_1st_week = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', self.employee_bert.resource_id.ids, datetime(2025, 8, 16), datetime(2025, 8, 23, 23, 59)
        )

        self.assertEqual(self.slot.allocated_hours, 40.0)
        self.assertEqual(planning_hours_info_1st_week[self.employee_bert.resource_id.id]['value'], 16)

        planning_hours_info_2nd_week = self.env['planning.slot']._gantt_progress_bar(
            'resource_id', self.employee_bert.resource_id.ids, datetime(2025, 8, 24), datetime(2025, 8, 30, 23, 59)
        )

        self.assertEqual(planning_hours_info_2nd_week[self.employee_bert.resource_id.id]['value'], 24)

    def test_compute_slots_data(self):
        """Test that planning.send wizard computes slot_ids and employee_ids correctly, including active_domain."""
        # Create two employees
        employee_a, employee_b = self.env['hr.employee'].create([
            {'name': 'Employee A'},
            {'name': 'Employee B'},
        ])

        # Create a planning role
        role_dev, role_other = self.env['planning.role'].create([
            {'name': 'Dev'},
            {'name': 'Tester'},
        ])

        # Create slots: one in range (role = Tester), one out of range
        slot_in_range = self.env['planning.slot'].create([
            {
                'start_datetime': datetime(2023, 11, 20, 9, 0),
                'end_datetime': datetime(2023, 11, 20, 16, 0),
                'employee_id': employee_a.id,
                'resource_id': employee_a.resource_id.id,
                'resource_type': 'user',
                'role_id': role_other.id,
            },
            {
                'start_datetime': datetime(2023, 11, 19, 9, 0),
                'end_datetime': datetime(2023, 11, 19, 16, 0),
                'employee_id': employee_b.id,
                'resource_id': employee_b.resource_id.id,
                'resource_type': 'user',
                'role_id': role_dev.id,
            },
        ])
        slot_in_range = slot_in_range[0]

        # Create wizard with a time window that only includes slot_in_range
        wizard = self.env['planning.send'].create({
            'start_datetime': datetime(2023, 11, 20, 8, 0),
            'end_datetime': datetime(2023, 11, 20, 17, 0),
        })
        wizard._compute_slots_data()

        # Wizard should only include slot_in_range
        self.assertIn(slot_in_range, wizard.slot_ids, "Wizard should include slots inside the range.")

        # Employee_ids should match employee of slot_in_range
        self.assertEqual(
            wizard.employee_ids,
            employee_a,
        )

        # Now test with active_domain filtering by role = Dev → should exclude slot_in_range
        wizard_ctx = wizard.with_context(active_domain=[('role_id', '=', role_dev.id)])
        wizard_ctx._compute_slots_data()
        self.assertFalse(
            wizard_ctx.slot_ids,
        )

    def test_planning_send_action_check_emails(self):
        start_datetime = datetime(2024, 7, 1, 8, 0)
        end_datetime = datetime(2024, 7, 1, 17, 0)
        beth_shift, joseph_shift = self.env['planning.slot'].create([
            {'start_datetime': start_datetime, 'end_datetime': end_datetime, 'resource_id': self.resource_bert.id},
            {'start_datetime': start_datetime, 'end_datetime': end_datetime, 'resource_id': self.resource_joseph.id},
        ])
        self.assertEqual(beth_shift.state, 'draft', 'The shift should be in draft state by default')
        self.assertEqual(joseph_shift.state, 'draft', 'The shift should be in draft state by default')

        self.employee_bert.work_email = ''

        planning_send_wizard = self.env['planning.send'].create({
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'slot_ids': (beth_shift + joseph_shift).ids,
        })
        self.assertTrue(self.env['hr.employee'].has_access('write'))
        action = planning_send_wizard.action_check_emails()
        self.assertEqual(action['name'], 'No Email Address for Some Employees')
        self.assertEqual(action['type'], 'ir.actions.act_window', 'The action should open a form view to complete missing work email')

        # since the user has no access in edit to `hr.employee`, we will not send the planning to the employee without email set.
        self.assertFalse(self.env['hr.employee'].with_user(self.planning_manager_user).has_access('write'))
        action = planning_send_wizard.with_user(self.planning_manager_user).action_check_emails()
        self.assertEqual(action['type'], 'ir.actions.client', 'The action should return a notification')
        self.assertEqual(action['tag'], 'display_notification', 'The action should return a notification')
        self.assertDictEqual(action['params'], {
            'type': 'info',
            'message': "Shifts published — employees without a work email were skipped",
            'next': {'type': 'ir.actions.act_window_close'},
        })
        self.assertEqual(beth_shift.state, 'draft', 'The shift should not be in published state after sending the planning since the employee set has no work_email and so no way to receive the planning')
        self.assertEqual(joseph_shift.state, 'published', 'The shift should be in published state after sending the planning')

    @freeze_time("2026-02-26 14:59:59")
    def test_shift_template_updates_end_date(self):
        """checks that, despite an employee having a fixed schedule, the start and end hours of their shift
        will correspond to the applied shift template."""
        planning_role = self.env['planning.role'].create({
            'name': 'role for template',
        })
        self.employee_joseph.write({'default_planning_role_id': planning_role.id})
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 11,
            'end_time': 19,
            'role_id': planning_role.id
        })
        with Form(self.env['planning.slot']) as slot:
            slot.role_id = planning_role
            slot.resource_id = self.employee_joseph.resource_id
            slot.template_id = template_slot
            self.assertEqual(slot.start_datetime, datetime.now().date() + relativedelta(hour=11, minute=0, second=0))
            self.assertEqual(slot.end_datetime, datetime.now().date() + relativedelta(hour=19, minute=0, second=0))

    def test_planning_gantt_unavailabilities_flexible_employee(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
        })
        employee.resource_id.calendar_id = self.flex_40h_calendar

        unavailabilities = self.env['planning.slot']._gantt_unavailability(
            'resource_id',
            [employee.resource_id.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'week',
        )
        self.assertNotIn(employee.resource_id.id, unavailabilities)
