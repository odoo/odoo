from odoo import fields

from odoo.exceptions import AccessError

from odoo.tests.common import new_test_user
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
from datetime import timedelta


class TestAccessRightsTimesheetGrid(TestCommonTimesheet):

    def setUp(self):
        super(TestAccessRightsTimesheetGrid, self).setUp()

        self.user_approver = new_test_user(self.env, 'user_approver', groups='hr_timesheet.group_hr_timesheet_approver')

        self.empl_approver = self.env['hr.employee'].create({
            'name': 'Empl Approver 1',
            'user_id': self.user_approver.id,
            'timesheet_manager_id': self.user_manager.id,
        })

        self.user_approver2 = new_test_user(self.env, 'user_approver2', groups='hr_timesheet.group_hr_timesheet_approver')

        self.empl_approver2 = self.env['hr.employee'].create({
            'name': 'Empl Approver 2',
            'user_id': self.user_approver2.id,
            'timesheet_manager_id': self.user_approver.id,
        })

        self.empl_employee.write({
            'timesheet_manager_id': self.user_approver.id
        })

        today = fields.Date.today()

        self.timesheet = self.env['account.analytic.line'].with_user(self.user_approver).create({
            'name': 'My timesheet 1',
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': today - timedelta(days=1),
            'unit_amount': 2,
            'employee_id': self.empl_employee.id
        })

        self.user_employee3 = new_test_user(self.env, 'user_employee3', groups='hr_timesheet.group_hr_timesheet_user')

        self.empl_employee3 = self.env['hr.employee'].create({
            'name': 'User Empl Employee 3',
            'user_id': self.user_employee3.id,
            'timesheet_manager_id': self.user_approver.id
        })

        self.timesheet2 = self.env['account.analytic.line'].with_user(self.user_approver).create({
            'name': 'My timesheet 4',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today - timedelta(days=1),
            'unit_amount': 2,
            'employee_id': self.empl_employee3.id
        })

        self.timesheet3 = self.env['account.analytic.line'].with_user(self.user_manager).create({
            'name': 'My old timesheet',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today - timedelta(days=10),
            'unit_amount': 2,
            'employee_id': self.empl_employee3.id,
        })

        self.timesheet4 = self.env['account.analytic.line'].with_user(self.user_manager).create({
            'name': 'My old timesheet 2',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today - timedelta(days=10),
            'unit_amount': 2,
            'employee_id': self.empl_employee2.id,
        })

        self.project_follower = self.env['project.project'].create({
            'name': "Project with visibility set on 'Invited employees'",
            'allow_timesheets': True,
            'privacy_visibility': 'followers',
        })
        # Prevent access right errors in test_access_rights_for_* methods
        self.project_follower.message_subscribe(partner_ids=[
            self.user_approver.partner_id.id, self.user_employee.partner_id.id, self.user_manager.partner_id.id
        ])

        self.timesheet_approver2 = self.env['account.analytic.line'].with_user(self.user_approver2).create({
            'name': 'Timesheet Approver2',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today - timedelta(days=1),
            'unit_amount': 1,
            'employee_id': self.empl_approver2.id
        })

        self.user_employee4 = new_test_user(self.env, 'user_employee4', groups='hr_timesheet.group_hr_timesheet_user')

        self.empl_employee4 = self.env['hr.employee'].create({
            'name': 'User Empl Employee 4',
            'user_id': self.user_employee4.id,
        })

        self.timesheet5 = self.env['account.analytic.line'].with_user(self.user_approver).create({
            'name': 'My timesheet 5',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today - timedelta(days=1),
            'unit_amount': 2,
            'employee_id': self.empl_employee4.id
        })

    def test_access_rights_for_employee(self):
        """ Check the operations of employee with the lowest access

            The employee with the lowest access rights can only :
                - read/write/create/delete his own timesheets
        """
        # Employee 1 create a timesheet for him
        timesheet_user1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'timesheet for employee 1',
            'unit_amount': 1
        })

        with self.assertRaises(AccessError):
            # employee 2 want to read the timesheet of employee 1
            timesheet_user1.with_user(self.user_employee2).read([])

            # employee 2 want to modity the timesheet of employee 1
            timesheet_user1.with_user(self.user_employee2).write({
                'unit_amount': 0.5
            })

            # employee 2 want to unlink a timesheet of employee 1
            timesheet_user1.with_user(self.user_employee2).unlink()

            # employee 1 want to create a timesheet for employee 2
            self.env['account.analytic.line'].with_user(self.user_employee).create({
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'name': 'a second timesheet for employee 2',
                'unit_amount': 8,
                'employee_id': self.empl_employee2.id
            })

        # employee 1 update his timesheet
        timesheet_user1.with_user(self.user_employee).write({
            'unit_amount': 5
        })

        # check if the updating is correct
        self.assertEqual(timesheet_user1.unit_amount, 5)

        # employee 1 remove his timesheet
        timesheet_user1.with_user(self.user_employee).unlink()

    def test_access_rights_for_approver(self):
        """ Check the operations of the employee with the access rights 'approver'

            The approver can read/write/create/delete all timesheets.
        """
        # The approver can create a timesheet for a employee
        timesheet_user1 = self.env['account.analytic.line'].create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'timesheet for employee 1',
            'unit_amount': 1,
            'employee_id': self.empl_employee.id
        })

        # the approver can read the timesheet of employee 1
        res = timesheet_user1.with_user(self.user_approver).read(['name'])
        self.assertEqual(timesheet_user1.name, res[0]['name'])

        # the approver can update the timesheet of employee 1
        timesheet_user1.with_user(self.user_approver).write({
            'unit_amount': 5
        })
        self.assertEqual(timesheet_user1.unit_amount, 5)

        # the approver can delete the timesheet of employee 1
        timesheet_user1.with_user(self.user_approver).unlink()

    def test_access_rights_for_manager(self):
        """ Check the operations of the administrator

            The manager (administrator) can read/write/create/delete all
            timesheets.
        """
        # The manager can create a timesheet for a employee
        timesheet_user1 = self.env['account.analytic.line'].create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'timesheet for employee 1',
            'unit_amount': 1,
            'employee_id': self.empl_employee.id
        })

        # the manager can read the timesheet of employee 1
        res = timesheet_user1.with_user(self.user_manager).read(['name'])
        self.assertEqual(timesheet_user1.name, res[0]['name'])

        # the manager can update the timesheet of employee 1
        timesheet_user1.with_user(self.user_manager).write({
            'unit_amount': 5
        })
        self.assertEqual(timesheet_user1.unit_amount, 5)

        # the manager can delete the timesheet of employee 1
        timesheet_user1.with_user(self.user_manager).unlink()

    def test_timesheet_validation_approver_and_invalidate(self):
        """ Check if the approver who has created the timesheet for an employee, can validate the timesheet."""
        timesheet_to_validate = self.timesheet
        timesheet_to_validate.with_user(self.user_approver).action_validate_timesheet()
        self.assertTrue(timesheet_to_validate.validated)
        timesheet_to_validate.with_user(self.user_approver).action_invalidate_timesheet()
        self.assertFalse(timesheet_to_validate.validated)

    def test_timesheet_validation_approver_own_timesheet(self):
        """ Check that the approver cannot validate his/her own timesheet.
        But the manager can approve it."""
        timesheet_to_validate = self.timesheet_approver2
        timesheet_to_validate.with_user(self.user_approver2).action_validate_timesheet()
        self.assertFalse(timesheet_to_validate.validated)
        timesheet_to_validate.with_user(self.user_approver).action_validate_timesheet()
        self.assertTrue(timesheet_to_validate.validated)

    def test_timesheet_validation_by_approver_when_he_is_not_responsible(self):
        """Check if an approver can validate an timesheet, if he isn't the Timesheet Responsible."""
        timesheet_to_validate = self.timesheet2

        # Normally the approver can't validate the timesheet because he doesn't know the project (and he isn't the manager of the employee) and he's not the Timesheet Responsible
        res = timesheet_to_validate.with_user(self.user_approver2).action_validate_timesheet()
        self.assertEqual(res['params']['type'], 'danger')
        self.assertEqual(timesheet_to_validate.validated, False)

    def test_timesheet_validation_by_approver_when_he_is_manager_of_employee(self):
        """Check if an approver can validate the timesheets into this project, when he is the manager of the employee."""
        timesheet_to_validate = self.timesheet2
        timesheet_to_validate.with_user(self.user_approver).action_validate_timesheet()
        self.assertEqual(timesheet_to_validate.validated, True)

    def test_show_timesheet_only_if_user_follow_project(self):
        """
            Test if the user cannot see the timesheets into a project when this project with visibility set on 'Invited employee', this user has the access right : 'See my timesheets' and he doesn't follow the project.
        """
        Timesheet = self.env['account.analytic.line']
        Partner = self.env['res.partner']
        partner = Partner.create({
            'name': self.user_manager.name,
            'email': self.user_manager.email
        })

        self.user_manager.write({
            'partner_id': partner.id
        })

        self.project_follower.message_subscribe(partner_ids=[self.user_manager.partner_id.id])

        timesheet = Timesheet.with_user(self.user_manager).create({
            'project_id': self.project_follower.id,
            'name': '/'
        })

        with self.assertRaises(AccessError):
            timesheet.with_user(self.user_employee).read()
            timesheet.with_user(self.user_approver).read()

    def test_employee_update_validated_timesheet(self):
        """
            Check an user with access right 'See own timesheet'
            cannot update his timesheet when it's validated.
        """
        timesheet_to_validate = self.timesheet
        timesheet_to_validate.with_user(self.user_approver).action_validate_timesheet()
        self.assertEqual(self.timesheet.validated, True)
        with self.assertRaises(AccessError):
            self.timesheet.with_user(self.user_employee).write({'unit_amount': 10})

        self.assertEqual(self.timesheet.unit_amount, 2)

    def test_employee_validate_timesheet(self):
        """
            Check an user with the lowest access right
            cannot validate any timesheets.
        """
        timesheet_to_validate = self.timesheet
        res = timesheet_to_validate.with_user(self.user_employee).action_validate_timesheet()
        self.assertEqual(res['params']['type'], 'danger')
        self.assertEqual(self.timesheet.validated, False)

    def test_employee_read_timesheet_of_other_employee(self):
        """ Check if the employee with the lowest access right
            cannot read timesheet of another employee
        """
        with self.assertRaises(AccessError):
            self.timesheet.with_user(self.user_employee3).read([])
            self.timesheet.with_user(self.user_employee2).read([])

        # the employee 1 can read this timesheet because his own
        res = self.timesheet.with_user(self.user_employee).read(['name'])
        self.assertEqual(res[0]['name'], 'My timesheet 1')

    def test_last_validated_timesheet_date(self):
        """ Check if an employee cannot create, modify or
            delete a timesheet with date <= last_validated_timesheet_date
        """
        self.assertFalse(self.empl_employee3.last_validated_timesheet_date)
        timesheet = self.env['account.analytic.line'].with_user(self.user_employee3).create({
            'name': 'timesheet',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': fields.Datetime.today() - timedelta(days=40),
            'unit_amount': 2,
            'employee_id': self.empl_employee3.id,
        })
        timesheet.with_user(self.user_approver).action_validate_timesheet()

        self.assertEqual(self.empl_employee3.last_validated_timesheet_date, timesheet.date)
        timesheet.with_user(self.user_approver).action_invalidate_timesheet()
        self.assertFalse(self.empl_employee3.last_validated_timesheet_date)

        # User can create timesheet with any date if timesheet.employee_id.last_validated_timesheet_date = False
        yesterday = fields.Date.today() - timedelta(days=1)
        timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee3).create({
            'name': 'timesheet 1',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': yesterday,
            'unit_amount': 2,
            'employee_id': self.empl_employee3.id,
        })
        self.timesheet4.write({'date': self.timesheet2.date})
        (self.timesheet3 + self.timesheet2 + self.timesheet4).action_validate_timesheet()
        self.assertEqual(self.empl_employee3.last_validated_timesheet_date, max(self.timesheet3.date, self.timesheet2.date))

        # User cannot delete timesheet if date <= timesheet.employee_id.last_validated_timesheet_date
        with self.assertRaises(AccessError):
            timesheet1.unlink()

        # User cannot create timesheet if date <= timesheet.employee_id.last_validated_timesheet_date
        with self.assertRaises(AccessError):
            self.env['account.analytic.line'].with_user(self.user_employee3).create({
                'name': 'timesheet',
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'date': fields.Datetime.today() - timedelta(days=10),
                'unit_amount': 2,
                'employee_id': self.empl_employee3.id,
            })

        # User can create timesheet if date > timesheet.employee_id.last_validated_timesheet_date
        timesheet = self.env['account.analytic.line'].with_user(self.user_employee3).create({
            'name': 'timesheet',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': fields.Datetime.today() + timedelta(days=10),
            'unit_amount': 2,
            'employee_id': self.empl_employee3.id,
        })

        # User cannot modify timesheet if date <= timesheet.employee_id.last_validated_timesheet_date
        with self.assertRaises(AccessError):
            timesheet.with_user(self.user_employee3).write({
                'date': fields.Datetime.today() - timedelta(days=10),
            })

        timesheet.with_user(self.user_approver).action_validate_timesheet()
        self.assertEqual(self.empl_employee3.last_validated_timesheet_date, yesterday)

        (timesheet + self.timesheet2 + self.timesheet4).with_user(self.user_approver).action_invalidate_timesheet()
        self.assertEqual(self.empl_employee3.last_validated_timesheet_date, self.timesheet3.date)

        self.timesheet3.with_user(self.user_approver).action_invalidate_timesheet()
        self.assertFalse(self.empl_employee3.last_validated_timesheet_date)

    def test_old_timesheet(self):
        """ Check that an employee cannot start a timesheet with date <= last_validated_timesheet_date
            and that validating a timesheet interrupts the potential running older timesheet
        """
        today = fields.Date.today()
        timesheet1, timesheet2, timesheet3, timesheet4 = self.env['account.analytic.line'].with_user(self.user_employee3).create([
            {
                'name': 'Timesheet1',
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'unit_amount': 2,
                'employee_id': self.empl_employee3.id,
            }, {
                'name': 'Timesheet2',
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'date': today - timedelta(days=2),
                'unit_amount': 2,
                'employee_id': self.empl_employee3.id,
            }, {
                'name': 'Timesheet3',
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'date': today - timedelta(days=1),
                'unit_amount': 2,
                'employee_id': self.empl_employee3.id,
            }, {
                'name': 'Timesheet4',
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'date': today,
                'unit_amount': 2,
                'employee_id': self.empl_employee3.id,
            },
        ])

        # The validation of a timesheet interrupts the timer of the running older timesheet
        timesheet1.with_user(self.user_employee3).action_timer_start()
        timesheet1.write({'date': today - timedelta(days=3)})  # simulate the user forgot to stop his timer.
        self.assertTrue(timesheet1.is_timer_running)
        timesheet2.with_user(self.user_approver).action_validate_timesheet()
        self.assertFalse(timesheet1.is_timer_running)

        # Starting the timer of a timesheet older than the last validated timesheet doesn't start
        # the timesheet timer but creates a new timesheet for the same task at the current date
        timesheet1.with_user(self.user_employee3).action_timer_start()
        self.assertFalse(timesheet1.is_timer_running)
        timesheet5 = self.env['account.analytic.line'].search(
            [('employee_id', '=', self.empl_employee3.id), ('is_timer_running', '=', True)])
        self.assertEqual(len(timesheet5), 1)
        self.assertEqual(timesheet5.project_id, self.project_customer)
        self.assertEqual(timesheet5.task_id, self.task1)
        self.assertEqual(timesheet5.date, today)

        # The employee can interrupt the new timesheet timer
        timesheet5.with_user(self.user_employee3).action_timer_stop()
        self.assertFalse(timesheet5.is_timer_running)

        # The validation of a timesheet doesn't interrupt the timer of a more recent timesheet
        timesheet4.with_user(self.user_employee3).action_timer_start()
        self.assertTrue(timesheet4.is_timer_running)
        timesheet3.with_user(self.user_approver).action_validate_timesheet()
        self.assertTrue(timesheet4.is_timer_running)

    def test_approve_user_without_approver_and_parents(self):
        """
            Check that a user with group_hr_timesheet_user can approve timesheets
            of user that don't have a timesheet approver and a parent.
        """
        timesheet_to_validate = self.timesheet5
        timesheet_to_validate.with_user(self.user_approver).action_validate_timesheet()
        self.assertEqual(timesheet_to_validate.validated, True)

    def test_update_timesheet_from_archived_employee(self):
        """
            Check the approver can alter a timesheet of an archived employee.

            Test Cases:
                - Create a timesheet for an employee
                - Archive the employee
                - Update the timesheet
                - Approve the timesheet
                - Update the timesheet
        """
        self.empl_employee3.active = False
        self.assertEqual(self.timesheet2.employee_id, self.empl_employee3, "The timesheet should be for the archived employee")
        self.assertEqual(self.timesheet2.unit_amount, 2, "The timesheet should have 2 hours")
        self.assertEqual(self.timesheet2.validated, False, "The timesheet should not be validated")
        self.timesheet2.with_user(self.user_approver).write({'unit_amount': 3})
        self.assertEqual(self.timesheet2.unit_amount, 3, "The timesheet should have 3 hours")

        self.timesheet2.with_user(self.user_approver).action_validate_timesheet()
        self.assertEqual(self.timesheet2.validated, True, "The timesheet should be validated")
        self.timesheet2.with_user(self.user_approver).write({'unit_amount': 4})
        self.assertEqual(self.timesheet2.unit_amount, 4, "The timesheet should have 4 hours")

    def test_recursive_approver_validation(self):
        """Check that a timesheet of an employee can be validated and then edited by its n+2 approver"""

        # Check that both approver and approver 2 are team approvers and not full managers
        # If the n+2 approver would be full manager, he would be allowed in any case to validate
        self.assertFalse(self.empl_approver.user_id.has_group("hr_timesheet.group_timesheet_manager"))
        self.assertFalse(self.empl_approver2.user_id.has_group("hr_timesheet.group_timesheet_manager"))

        # Create a hierarchy employee -> approver 2 -> approver
        self.empl_employee.parent_id = self.empl_approver2
        self.empl_employee.timesheet_manager_id = self.empl_approver2.user_id
        self.empl_approver2.parent_id = self.empl_approver
        self.empl_approver2.timesheet_manager_id = self.empl_approver.user_id

        # Check the timsheet is assigned to the lowest employee in the hierarchy
        self.assertEqual(self.timesheet.employee_id, self.empl_employee)

        # Check the n+2 approver can validate the timesheet
        self.timesheet.with_user(self.user_approver).action_validate_timesheet()

        # Check the n+2 approver can edit the validated timesheet
        self.timesheet.with_user(self.user_approver).date = fields.Date.today() - timedelta(days=2)
