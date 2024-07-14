# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from odoo.exceptions import UserError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import Form
from odoo.tests import new_test_user

from odoo.addons.mail.tests.common import MockEmail
from .common import TestCommonPlanning

class TestPlanning(TestCommonPlanning, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.datetime.now)
        with freeze_time('2019-5-1'):
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
        calendar = cls.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        cls.env.user.company_id.resource_calendar_id = calendar
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
            'duration': 4,
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
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-26 00:00:00',
            default_end_datetime='2019-06-26 23:59:59',
            default_resource_id=self.resource_joseph.id)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 26, 00, 0), 'It should still be the default start_datetime 0am')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 26, 23, 59, 59), 'It should adjust to employee calendar: 0am -> 9pm')

    def test_create_without_employee(self):
        """ This test objective is to test the default values when creating a new shift when no employee is set """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-27 00:00:00',
            default_end_datetime='2019-06-27 23:59:59',
            default_resource_id=False)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 27, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 27, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')

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
            1) Create a planning.slot.template with start_hours = 11 pm and duration = 3 hours.
            2) Create a planning.slot for one day and add the template.
            3) Check if the start and end dates are on two days and not one.
            4) Check if the allocating hours is equal to the duration in the template.
        """
        self.resource_bert.calendar_id = False
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 23,
            'duration': 3,
        })

        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 1, 0, 0),
            'end_datetime': datetime(2021, 1, 1, 23, 59),
            'resource_id': self.resource_bert.id,
        })

        slot.write({
            'template_id': template_slot.id,
        })

        self.assertEqual(slot.start_datetime, datetime(2021, 1, 1, 23, 0), 'The start datetime should have the same hour and minutes defined in the template in the resource timezone.')
        self.assertEqual(slot.end_datetime, datetime(2021, 1, 2, 2, 0), 'The end datetime of this slot should be 3 hours after the start datetime as mentionned in the template in the resource timezone.')
        self.assertEqual(slot.allocated_hours, 3, 'The allocated hours of this slot should be the duration defined in the template in the resource timezone.')

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
            'duration': 5.0,
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

    def test_name_long_duration(self):
        """ Set an absurdly high duration to ensure we validate it and get an error """
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 9,
            'duration': 100000,
        })
        with self.assertRaises(ValidationError):
            # only try to get the name, this triggers its compute
            template_slot.name

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
            'duration': 2.0,
            'role_id': role_a.id
        })
        self.assertEqual(template_a.duration_days, 1, "Duration in days should be a 1 day according to resource calendar.")
        self.assertEqual(template_a.end_time, 10.0, "End time should be 2 hours from start hours.")

        template_b = PlanningTemplate.create({
            'start_time': 8,
            'duration': 4.0,
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
            'duration': 5.1,  # corresponds to 5:06
        })
        self.assertEqual(template.start_time + template.duration, 13.1, 'Template end time should be the start + duration')
        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 1, 0, 0),
            'end_datetime': datetime(2021, 1, 1, 23, 59),
        })
        slot.write({
            'template_id': template.id,
        })
        self.assertEqual(slot.end_datetime.minute, 6, 'The min should be 6, just like in the template, not 5 due to rounding error')

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
        employee.resource_id.calendar_id = False

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
        # Create an employee linked to this calendar
        night_employee = self.env['hr.employee'].create({
            'name': 'Night employee',
            'resource_calendar_id': night_shifts_calendar.id,
        })

        # Create a shift from 21:30 to 6:00 with an allocated 8 hours
        night_shift = self.env['planning.slot'].create({
            'name': 'Night Shift',
            'start_datetime': datetime(2024, 5, 10, 21, 30),
            'end_datetime': datetime(2024, 5, 11, 6, 0),
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
