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

    def test_portal_task_hours_no_double_counting(self):
        """ Test that totals for both allocated and spent hours are calculated correctly, preventing double-counting.

            Test Cases:
            1. Parent + all sub-tasks in same group -> Totals are based on the parent.
            2. Parent alone in group -> Totals are based on the parent's value.
            3. Sub-task alone in group -> Totals are based on the sub-task's value.
            4. Parent + distant sub-task in same group -> Totals are based on the parent.
        """

        parent_task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': self.project_portal.id,
            'allocated_hours': 500.0,
        })
        sub_task_1 = self.env['project.task'].create({
            'name': 'Sub-task 1',
            'project_id': self.project_portal.id,
            'parent_id': parent_task.id,
            'allocated_hours': 50.0,
        })
        sub_task_2 = self.env['project.task'].create({
            'name': 'Sub-task 2',
            'project_id': self.project_portal.id,
            'parent_id': sub_task_1.id,
            'allocated_hours': 25.0,
        })

        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.env['account.analytic.line'].create([
            {'name': 'Time on parent', 'project_id': self.project_portal.id, 'task_id': parent_task.id, 'unit_amount': 50, 'employee_id': employee.id},
            {'name': 'Time on sub-task 1', 'project_id': self.project_portal.id, 'task_id': sub_task_1.id, 'unit_amount': 25, 'employee_id': employee.id},
            {'name': 'Time on sub-task 2', 'project_id': self.project_portal.id, 'task_id': sub_task_2.id, 'unit_amount': 15, 'employee_id': employee.id},
        ])

        # Test Case 1: A group containing parent and its all sub-tasks
        group_with_all_tasks = parent_task | sub_task_1 | sub_task_2
        result_group_all = group_with_all_tasks._get_portal_total_hours_dict()
        self.assertEqual(result_group_all.get('allocated_hours'), 500.0, "Should only count the parent's allocated hours (500h).")
        self.assertEqual(result_group_all.get('effective_hours'), 90.0, "Should be the parent's total hours spent (90h).")

        # Test Case 2: A group containing only the parent task
        result_group_parent_only = parent_task._get_portal_total_hours_dict()
        self.assertEqual(result_group_parent_only.get('allocated_hours'), 500.0, "Should be the parent's allocated hours (500h).")
        self.assertEqual(result_group_parent_only.get('effective_hours'), 90.0, "Should be the parent's total hours spent (90h).")

        # Test Case 3: A group containing only the intermediate sub-task
        result_group_sub_only = sub_task_1._get_portal_total_hours_dict()
        self.assertEqual(result_group_sub_only.get('allocated_hours'), 50.0, "Should be the sub-task's allocated hours (50h).")
        self.assertEqual(result_group_sub_only.get('effective_hours'), 40.0, "Should be the sub-task's total hours spent (40h).")

        # Test Case 4: A group with a parent and a distant sub-task
        group_with_ancestor = parent_task | sub_task_2
        result_group_ancestor = group_with_ancestor._get_portal_total_hours_dict()
        self.assertEqual(result_group_ancestor.get('allocated_hours'), 500.0, "Should only count the parent's allocated hours (500h).")
        self.assertEqual(result_group_ancestor.get('effective_hours'), 90.0, "Should be the parent's total hours spent (90h).")
