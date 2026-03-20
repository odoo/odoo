# -*- coding: utf-8 -*-

from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon

@tagged('post_install', '-at_install')
class TestPortalTimesheet(TestProjectSharingCommon):

    def test_ensure_fields_view_get_access(self):
        """ Ensure that the method _fields_view_get is accessible without
            raising an error for all portal users
        """
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        for view in ['form', 'list']:
            # Ensure that uom.uom records are not present in cache
            self.env.invalidate_all()
            # Should not raise any access error
            self.env['account.analytic.line'].with_user(self.user_portal).get_view(view_type=view)

    def test_action_view_subtask_timesheet(self):
        """ Ensure that the action view_subtask_timesheet is accessible without
            raising an error for all portal users
        """
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        action = self.task_portal.action_view_subtask_timesheet()
        tree_view_id = form_view_id = kanban_view_id = False
        for view_id, view_type in action['views']:
            if view_type == 'list':
                tree_view_id = view_id
            elif view_type == 'form':
                form_view_id = view_id
            elif view_type == 'kanban':
                kanban_view_id = view_id

        action = self.task_portal.with_user(self.user_portal).action_view_subtask_timesheet()
        portal_tree_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.hr_timesheet_line_portal_tree')
        portal_form_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.timesheet_view_form_portal_user')
        portal_kanban_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.view_kanban_account_analytic_line_portal_user')
        if portal_tree_view_id and portal_form_view_id and portal_kanban_view_id:
            # no need to check that if the views are not installed or already removed
            for view_id, view_type in action['views']:
                if view_type == 'list':
                    self.assertEqual(view_id, portal_tree_view_id)
                elif view_type == 'form':
                    self.assertEqual(view_id, portal_form_view_id)
                elif view_type == 'kanban':
                    self.assertEqual(view_id, portal_kanban_view_id)

            self.env['ir.ui.view'].browse([portal_tree_view_id, portal_form_view_id, portal_kanban_view_id]).unlink()

        action = self.task_portal.with_user(self.user_portal).action_view_subtask_timesheet()
        for view_id, view_type in action['views']:
            if view_type == 'list':
                self.assertEqual(view_id, tree_view_id)
            elif view_type == 'form':
                self.assertEqual(view_id, form_view_id)
            elif view_type == 'kanban':
                self.assertEqual(view_id, kanban_view_id)

    def test_timesheet_visibility_portal(self):
        """
        Steps:
        1. Retrieve the domain that determines timesheet visibility for the portal user.
        2. Create an employee linked to the project user.
        3. Create a timesheet entry associated with a specific project and task.
        4. Assign the portal user as the partner on the task.
        5. Search for timesheets using the retrieved domain.
        6. Verify that the created timesheet is visible to the portal user.
        7. Remove the portal user as the partner of the task.
        8. Search for timesheets again using the same domain.
        9. Verify that the timesheet is no longer visible to the portal user.
        10. Assign the portal user as the partner of the project.
        11. Search for timesheets again using the same domain.
        12. Verify that the timesheet is now visible to the portal user.
        """
        AnalyticLineModel = self.env['account.analytic.line']
        timesheet_domain = AnalyticLineModel.with_user(self.user_portal)._timesheet_get_portal_domain()

        employee = self.env['hr.employee'].create({
            'name': 'Project User Employee',
            'user_id': self.user_projectuser.id,
        })

        timesheet_entry = AnalyticLineModel.create({
            'name': 'Timesheet',
            'project_id': self.project_cows.id,
            'task_id': self.task_cow.id,
            'employee_id': employee.id,
        })

        self.task_cow.write({'partner_id': self.user_portal.partner_id.id})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertIn(timesheet_entry.id, timesheets.ids, "Portal user should see the timesheet when set as the partner on the task.")

        self.task_cow.write({'partner_id': False})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertNotIn(timesheet_entry.id, timesheets.ids, "Portal user should not see the timesheet when not assigned as the task's partner.")

        self.project_cows.write({'partner_id': self.user_portal.partner_id.id})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertIn(timesheet_entry.id, timesheets.ids, "Portal user should see the timesheet when set as the project’s partner.")
