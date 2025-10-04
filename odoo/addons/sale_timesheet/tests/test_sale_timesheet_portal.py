# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet

@tagged('post_install', '-at_install')
class TestSaleTimesheetPortal(TestProjectSharingCommon, TestCommonSaleTimesheet):

    def test_ensure_allowed_so_line_field_access(self):
        """ Ensure that the field so_line of account.analytic.line is accessible for portal user"""
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_task_rate.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
            'privacy_visibility': 'portal',
            'message_partner_ids': [
                Command.link(self.user_portal.partner_id.id),
            ],
        })
        task1 = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_task_rate.id,
        })
        # log some timesheets (on the project accessible in portal)
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.project_task_rate.id,
            'task_id': task1.id,
            'unit_amount': 10.5,
            'employee_id': self.employee_user.id,
        })
        # Accessing field allowed_so_line_ids as a portal user should not raise any access error
        self.env.invalidate_all()
        timesheet1.with_user(self.user_portal).read(['allowed_so_line_ids'])
