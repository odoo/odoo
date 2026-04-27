# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from freezegun import freeze_time

from odoo.tests import tagged, Form
from odoo.exceptions import ValidationError

from .common import TestHelpdeskTimesheetCommon


@tagged('-at_install', 'post_install')
class TestTimesheet(TestHelpdeskTimesheetCommon):

    def test_timesheet_cannot_be_linked_to_task_and_ticket(self):
        """ Test if an exception is raised when we want to link a task and a ticket in a timesheet

            Normally, now we cannot have a ticket and a task in one timesheet.

            Test Case:
            =========
            1) Create ticket and a task,
            2) Create timesheet with this ticket and task and check if an exception is raise.
        """
        # 1) Create ticket and a task
        ticket = self.helpdesk_ticket
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
        })

        # 2) Create timesheet with this ticket and task and check if an exception is raise
        with self.assertRaises(ValidationError):
            self.env['account.analytic.line'].create({
                'name': 'Test Timesheet',
                'unit_amount': 1,
                'project_id': self.project.id,
                'helpdesk_ticket_id': ticket.id,
                'task_id': task.id,
                'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id,
            })

    def test_compute_timesheet_partner_from_ticket_customer(self):
        partner2 = self.env['res.partner'].create({
            'name': 'Customer ticket',
            'email': 'customer@ticket.com',
        })
        helpdesk_ticket = self.helpdesk_ticket
        timesheet_entry = self.env['account.analytic.line'].create({
            'name': 'the only timesheet. So lonely...',
            'helpdesk_ticket_id': helpdesk_ticket.id,
            'project_id': self.helpdesk_team.project_id.id,
            'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id,
        })

        self.assertEqual(timesheet_entry.partner_id, self.partner, "The timesheet entry's partner should be equal to the ticket's partner/customer")

        helpdesk_ticket.write({'partner_id': partner2.id})

        self.assertEqual(timesheet_entry.partner_id, partner2, "The timesheet entry's partner should still be equal to the ticket's partner/customer, after the change")

    def test_helpdesk_timesheet_wizard_timezones(self):
        user = self.user_employee
        wizard = self.env['helpdesk.ticket.create.timesheet'].with_user(user).create({
            'description': 'Create timesheet wizard',
            'ticket_id': self.helpdesk_ticket.id,
            'time_spent': 1.0,
        })
        timezones = [
            'Pacific/Niue',        # UTC-11,
            'Europe/Brussels',     # UTC+1
            'Pacific/Kiritimati',  # UTC+14
        ]
        test_cases = {
            '2024-01-24 08:30': (-1, +0, +0),
            '2024-01-24 10:30': (-1, +0, +1),
            '2024-01-24 16:30': (+0, +0, +1),
        }

        for utc_time, day_diffs in test_cases.items():
            with freeze_time(utc_time):
                day = date.today().day
                expected = (date(2024, 1, day + diff) for diff in day_diffs)
                for tz, local_date in zip(timezones, expected):
                    user.tz = tz
                    timesheet = wizard.action_generate_timesheet()
                    self.assertEqual(
                        timesheet.date,
                        local_date,
                        f"{utc_time} UTC should be {local_date} in {tz} time",
                    )

    def test_log_timesheet_with_ticket_analytic_account(self):
        """ Test whether the analytic account of the project is set on the ticket.

            Test Case:
            ----------
                1) Create Ticket
                2) Check the default analytic account of the project and ticket
        """

        helpdesk_ticket = self.helpdesk_ticket

        self.assertEqual(helpdesk_ticket.analytic_account_id, self.project.account_id)

    def test_compute_project_id(self):
        """ Test compute project_id works as expected when helpdesk_ticket_id changes on a timesheet """
        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        timesheet = self.env['account.analytic.line'].create({
            'name': '/',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'employee_id': self.empl_employee.id,
        })

        timesheet.helpdesk_ticket_id = helpdesk_ticket
        self.assertFalse(timesheet.task_id, "The task should be unset since a helpdesk ticket has been set on the timesheet")
        self.assertEqual(timesheet.project_id, self.project, "The project set on the timesheet should now the project on the helpdesk team of the ticket linked.")

    def test_timesheet_customer_association(self):
        employee = self.env['hr.employee'].create({'user_id': self.env.uid})
        ticket_form = Form(self.env['helpdesk.ticket'])
        ticket_form.partner_id = self.partner
        ticket_form.name = 'Test'
        ticket_form.team_id = self.helpdesk_team
        with ticket_form.timesheet_ids.new() as line:
            line.employee_id = employee
            line.name = "/"
            line.unit_amount = 3
        ticket = ticket_form.save()
        self.assertEqual(ticket.timesheet_ids.partner_id, ticket.partner_id, "The timesheet partner should be equal to the ticket's partner/customer")
        partner = self.env['res.partner'].create({
            'name': 'Customer ticket',
            'email': 'customer@ticket.com',
        })
        ticket.partner_id = partner
        self.assertEqual(ticket.timesheet_ids.partner_id, partner, "The partner set on the timesheet should follow the one set on the ticket linked.")

    def test_timesheet_bulk_creation_of_timesheets_for_seperate_ticket_id(self):
        """ Test whether creating timesheets in bulk for separate ticket ids works """
        # (1) create 2 tickets
        helpdesk_ticket_1, helpdesk_ticket_2 = self.env['helpdesk.ticket'].create([{
            'name': 'Test Ticket 1',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }, {
              'name': 'Test Ticket 2',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }])

        # (2) create timesheet for each ticket in a bulk create
        timesheet_1, timesheet_2 = self.env['account.analytic.line'].create([{
            'name': 'non valid timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_1.id,
            'employee_id': self.empl_employee.id,
        }, {
            'name': 'validated timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_2.id,
            'employee_id': self.empl_employee.id,
        }])

        # (3) Verify each timesheet exists
        self.assertTrue(timesheet_1, "Bulk creation of timesheets should work for separate ticket ids")
        self.assertTrue(timesheet_2, "Bulk creation of timesheets should work for separate ticket ids")
        self.assertEqual(timesheet_1.helpdesk_ticket_id, helpdesk_ticket_1)
        self.assertEqual(timesheet_2.helpdesk_ticket_id, helpdesk_ticket_2)

    def test_timesheet_ticket_consistency_when_helpdesk_team_change(self):
        """
            Test that the change of `helpdesk_team` of a helpdesk_ticket results in:
            - non-validated timesheets have the new project associated.
            - validated timesheets does not get change and keep the initial project.
        """
        self.env.user.tz = 'UTC'
        # Create ticket and store initial project (helpdesk_team)
        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        initial_project = helpdesk_ticket.project_id

        # create a valid timesheet and non-validated timesheet under the same helpdesk_ticket/project
        timesheet_valid, timesheet_non_valid = self.env['account.analytic.line'].create([{
            'name': 'valid timesheet test',
            'project_id': initial_project.id,
            'helpdesk_ticket_id': helpdesk_ticket.id,
            'employee_id': self.empl_employee.id,
        }, {
            'name': 'non valid timesheet test',
            'project_id': initial_project.id,
            'helpdesk_ticket_id': helpdesk_ticket.id,
            'employee_id': self.empl_employee.id,
        }])
        timesheet_valid.action_validate_timesheet()
        self.assertTrue(timesheet_valid.validated, "The timesheet should be validated.")

        # create a new project and helpdesk_team with timesheet feature
        new_project = self.env['project.project'].create({
            'name': 'Project 2',
            'allow_timesheets': True,
            'partner_id': self.partner.id,
        })
        new_helpdesk_team = self.env['helpdesk.team'].create({
            'name': 'Test Team 2',
            'use_helpdesk_timesheet': True,
            'project_id': new_project.id,
        })

        # change the helpdesk_team of the helpdesk_ticket
        form = Form(helpdesk_ticket)
        form.team_id = new_helpdesk_team
        form.save()
        self.assertEqual(timesheet_valid.project_id, initial_project,
                         "Validated timesheet should keep the same project when the helpdesk_ticket's helpdesk_team is changed.")
        self.assertEqual(timesheet_non_valid.project_id, new_project,
                         "Non-validated timesheet should have the new project set when the helpdesk_ticket's helpdesk_team is changed.")

    def test_timesheet_check_warning_when_helpdesk_team_change(self):
        """
            1)  Test that when a ticket changes its project (helpdesk_team), if the ticket contains at least one non-validated timesheet AND
                the new project has no timesheet feature available, a warning notification should be raised.
            2)  The tickets's helpdesk_team and non-validated timesheets should be changed despite the warning raised.
            3)  Checks that no warning is raised when the timesheets are validated.
        """
        self.env.user.tz = 'UTC'
        # (1) create tickets and timesheets
        helpdesk_ticket_non_valid, helpdesk_ticket_valid = self.env['helpdesk.ticket'].create([{
            'name': 'Test Ticket non valid',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }, {
              'name': 'Test Ticket only valid',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }])

        dummy, timesheet_validated = self.env['account.analytic.line'].create([{
            'name': 'non valid timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_non_valid.id,
            'employee_id': self.empl_employee.id,
        }, {
            'name': 'validated timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_valid.id,
            'employee_id': self.empl_employee.id,
        }])

        # create helpdesk_team without timesheet feature
        no_timesheet_helpdesk_team = self.env['helpdesk.team'].create({
            'name': 'Test Team with no timesheet',
            'use_helpdesk_timesheet': False,
        })

        # change the helpdesk_team of the ticket containing non-validated timesheet, to the helpdesk_team without timesheet feature
        helpdesk_ticket_non_valid.write({'team_id': no_timesheet_helpdesk_team.id})
        warning = helpdesk_ticket_non_valid._onchange_team_id()
        self.assertTrue(warning, "A warning should be raised when the ticket's timesheets are not all validated and the newly assigned helpdesk_team has no timesheet feature.")

        # (2) verify that after the warning, the helpdesk_team is changed
        self.assertEqual(helpdesk_ticket_non_valid.team_id, no_timesheet_helpdesk_team,
                         "The ticket's helpdesk_team should be changed despite the warning raised.")

        # (3) Create ticket including only validated timesheet
        timesheet_validated.action_validate_timesheet()
        self.assertTrue(timesheet_validated.validated, "The timesheet should be validated.")

        # change the helpdesk_team of the ticket only containing validated timesheet, to the helpdesk_team without timesheet feature
        helpdesk_ticket_valid.write({'team_id': no_timesheet_helpdesk_team.id})
        warning = helpdesk_ticket_valid._onchange_team_id()
        self.assertFalse(warning, "No warning should be raised when the ticket's timesheets are validated.")

    def test_default_company_id_for_timesheet(self):
        """ This test ensures that the default company_id used when a timesheet is created from the ticket form view is the company_id of its project. """
        new_company = self.env['res.company'].create({'name': "Do the extra miles"})
        company_second = self.env['res.company'].create({'name': "Second company"})
        self.env['hr.employee'].create({'user_id': self.env.uid, 'company_id': new_company.id})
        self.env['hr.employee'].create({'user_id': self.env.uid, 'company_id': company_second.id})
        project = self.env['project.project'].create({
            'name': 'Project',
            'allow_timesheets': True,
            'partner_id': self.partner.id,
        })
        helpdesk_team = self.env['helpdesk.team'].create({
            'name': 'Test Team new company',
            'use_helpdesk_timesheet': True,
            'project_id': project.id,
            'company_id': new_company.id,
        })
        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        # Use the default values sent by the form view
        vals = {'date': '2023-11-03', 'user_id': False, 'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id, 'name': False,
                'unit_amount': 0, 'project_id': self.project.id, 'task_id': False, 'helpdesk_ticket_id': helpdesk_ticket.id}
        timesheet = self.env['account.analytic.line'].create([vals])
        self.assertEqual(timesheet.company_id, new_company, 'The expected company of the timesheet is the company from the project of its ticket')

        # Test to ensure provided company_id is not overridden
        vals.update({'company_id': new_company.id, 'date': '2023-11-04', 'user_id': self.env.uid})
        vals.pop('employee_id')
        timesheet = self.env['account.analytic.line'].create([vals])
        self.assertEqual(timesheet.company_id, new_company, 'The expected company of the timesheet is the company from the project of its ticket')

    def test_launch_the_timer_for_a_ticket(self):
        """ Test if starting and stopping the timer on a timesheet entry linked to a helpdesk ticket creates a new entry
            with the ticket_id set
        """
        yesterday = date.today() - timedelta(days=1)

        timesheet = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': 'Yesterday Timesheet',
            'project_id': self.project.id,
            'date': yesterday,
            'employee_id': self.empl_employee.id,
            'helpdesk_ticket_id': self.helpdesk_ticket.id,
        })

        timesheet.with_user(self.user_employee).action_timer_start()
        timesheet.with_user(self.user_employee).action_timer_stop()

        timesheet_count = self.env['account.analytic.line'].search_count([
            ('date', '=', date.today()),
            ('helpdesk_ticket_id', '=', self.helpdesk_ticket.id)
        ], limit=1)
        self.assertEqual(timesheet_count, 1, "The new timesheet entry's ticket_id should be set correctly.")

    def test_create_separate_timesheet_entries_depending_on_ticket_id(self):
        ticket_copy = self.helpdesk_ticket.copy()
        timesheet_1, timesheet_2, timesheet_3 = self.env['account.analytic.line'].with_user(self.user_employee).create([{
            'name': '/',
            'project_id': self.project.id,
            'date': date.today(),
            'helpdesk_ticket_id': self.helpdesk_ticket.id,
        }, {
            'name': '/',
            'project_id': self.project.id,
            'date': date.today(),
            'helpdesk_ticket_id': ticket_copy.id,
        }, {
            'name': '/',
            'project_id': self.project.id,
            'date': date.today(),
            'helpdesk_ticket_id': ticket_copy.id,
        }])

        timesheet_1.sudo()._add_timesheet_time(15, True)
        timesheet_2.sudo()._add_timesheet_time(15, True)
        timesheet_3.sudo()._add_timesheet_time(15, True)

        # timesheets 2 and 3 should be merged since they belong to the same ticket, timesheet 1 must be kept separate
        self.assertTrue(timesheet_1.exists(), 'Timesheet 1 should not have been merged')
        self.assertFalse(timesheet_2.exists(), 'Timesheet 2 should have been merged into 3')
        self.assertTrue(timesheet_3.exists(), 'Timesheet 2 should have been merged into 3')
        self.assertAlmostEqual(timesheet_1.unit_amount, 0.25, 2)
        self.assertAlmostEqual(timesheet_3.unit_amount, 0.5, 2)

    def test_total_hours_spent(self):
        """ Test the total_hours_spent field is correctly computed """
        # create 5 tickets with a timesheet each of 10 minutes
        tickets = self.env['helpdesk.ticket'].create([{
            'name': f'Ticket {i}',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        } for i in range(5)])

        for ticket in tickets:
            self.env['account.analytic.line'].create({
                'name': 'Test Timesheet',
                'unit_amount': 1 / 6,  # 10 minutes in hours
                'project_id': self.project.id,
                'helpdesk_ticket_id': ticket.id,
                'employee_id': self.empl_employee.id,
            })

        # check sum of total_hours_spent is 5/6 hours
        total_hours_spent = sum(ticket.total_hours_spent for ticket in tickets)
        self.assertAlmostEqual(total_hours_spent, 5 / 6, places=2,
                               msg="The total hours spent across all tickets should be 5/6 hours (50 minutes).")
