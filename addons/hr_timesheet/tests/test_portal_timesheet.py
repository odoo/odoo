# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.discuss import Store
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

    def test_collaborators_accessible_by_timesheet_user(self):
        """Test that a restricted user (with only HR Timesheet User access) can
        access project collaborators (fetched when fetching a project) without
        getting an AccessError.
        """
        user = mail_new_test_user(
            self.env,
            login="employee_user",
            groups="hr_timesheet.group_hr_timesheet_user",
        )
        self.project_portal.collaborator_ids = [
            Command.create({"partner_id": self.partner_portal.id})
        ]
        store = Store()
        self.project_portal.with_user(user)._thread_to_store(store, request_list=["followers"])
        self.assertEqual(
            store.get_result()["mail.thread"][0]["collaborator_ids"],
            [{"id": self.partner_portal.id, "type": "partner"}],
        )
