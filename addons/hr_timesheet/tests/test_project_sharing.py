from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing_ui import TestProjectSharingUi


@tagged('post_install', '-at_install')
class TestProjectSharingHrTimesheet(TestProjectSharingUi):

    def test_portal_user_can_access_shared_global_project_with_timesheet_in_another_company(self):
        """
        A portal user from Company A should be able to access a global project
        (no company set) shared with them, even when a timesheet entry on that
        project was recorded under a different company (Company 2).
        """
        company_2 = self.env['res.company'].create({'name': 'Company 2'})
        employee = self.env['hr.employee'].create({
            'name': 'Employee',
            'company_id': company_2.id,
        })
        project_share_wizard = self.env['project.share.wizard'].create({
            'access_mode': 'edit',
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'partner_ids': [Command.link(self.partner_portal.id)],
        })
        project_share_wizard.action_send_mail()
        task_portal = self.env['project.task'].create({
            'name': 'Test',
            'project_id': self.project_portal.id,
        })
        self.env['account.analytic.line'].with_company(company_2).create({
            'project_id': self.project_portal.id,
            'task_id': task_portal.id,
            'name': 'Timesheet under Company 2',
            'unit_amount': 4,
            'employee_id': employee.id,
        })
        self.start_tour("/my/projects", 'portal_project_sharing_tour', login='georges1')
