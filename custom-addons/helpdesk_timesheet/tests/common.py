# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestHelpdeskTimesheetCommon(TestCommonTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        group_helpdesk_user = cls.env.ref('helpdesk.group_helpdesk_user')
        cls.user_manager.groups_id += group_helpdesk_user
        cls.user_employee.groups_id += group_helpdesk_user

        cls.partner = cls.env['res.partner'].create({
            'name': 'Customer Task',
            'email': 'customer@task.com',
        })

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Analytic Account for Test Customer',
            'partner_id': cls.partner.id,
            'plan_id': cls.analytic_plan.id,
            'code': 'TEST',
        })

        cls.project = cls.env['project.project'].create({
            'name': 'Project',
            'allow_timesheets': True,
            'partner_id': cls.partner.id,
        })

        cls.helpdesk_team = cls.env['helpdesk.team'].create({
            'name': 'Test Team',
            'use_helpdesk_timesheet': True,
            'project_id': cls.project.id,
        })

        cls.helpdesk_ticket = cls.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': cls.helpdesk_team.id,
            'partner_id': cls.partner.id,
        })
