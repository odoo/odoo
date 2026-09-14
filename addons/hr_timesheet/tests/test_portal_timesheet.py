from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon


@tagged("post_install", "-at_install")
class TestPortalTimesheet(TestProjectSharingCommon):
    def test_ensure_fields_view_get_access(self):
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        )
        for view in ["form", "list"]:
            self.env.invalidate_all()
            self.env["account.analytic.line"].with_user(self.user_portal).get_view(
                view_type=view
            )

    def test_action_view_subtask_timesheet(self):
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        )
        action = self.task_portal.action_view_subtask_timesheet()
        tree_view_id = form_view_id = kanban_view_id = False
        for view_id, view_type in action["views"]:
            if view_type == "list":
                tree_view_id = view_id
            elif view_type == "form":
                form_view_id = view_id
            elif view_type == "kanban":
                kanban_view_id = view_id

        action = self.task_portal.with_user(
            self.user_portal
        ).action_view_subtask_timesheet()
        portal_tree_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "hr_timesheet.hr_timesheet_line_portal_tree"
        )
        portal_form_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "hr_timesheet.timesheet_view_form_portal_user"
        )
        portal_kanban_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "hr_timesheet.view_kanban_account_analytic_line_portal_user"
        )
        if portal_tree_view_id and portal_form_view_id and portal_kanban_view_id:
            for view_id, view_type in action["views"]:
                if view_type == "list":
                    self.assertEqual(view_id, portal_tree_view_id)
                elif view_type == "form":
                    self.assertEqual(view_id, portal_form_view_id)
                elif view_type == "kanban":
                    self.assertEqual(view_id, portal_kanban_view_id)

            self.env["ir.ui.view"].browse(
                [portal_tree_view_id, portal_form_view_id, portal_kanban_view_id]
            ).unlink()

        action = self.task_portal.with_user(
            self.user_portal
        ).action_view_subtask_timesheet()
        for view_id, view_type in action["views"]:
            if view_type == "list":
                self.assertEqual(view_id, tree_view_id)
            elif view_type == "form":
                self.assertEqual(view_id, form_view_id)
            elif view_type == "kanban":
                self.assertEqual(view_id, kanban_view_id)

    def test_timesheet_visibility_portal(self):
        AnalyticLineModel = self.env["account.analytic.line"]
        timesheet_domain = AnalyticLineModel.with_user(
            self.user_portal
        )._timesheet_get_portal_domain()

        employee = self.env["hr.employee"].create(
            {
                "name": "Project User Employee",
                "user_id": self.user_projectuser.id,
            }
        )

        timesheet_entry = AnalyticLineModel.create(
            {
                "name": "Timesheet",
                "project_id": self.project_cows.id,
                "task_id": self.task_cow.id,
                "employee_id": employee.id,
            }
        )

        self.task_cow.write({"partner_id": self.user_portal.partner_id.id})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertIn(
            timesheet_entry.id,
            timesheets.ids,
            "Portal user should see the timesheet when set as the partner on the task.",
        )

        self.task_cow.write({"partner_id": False})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertNotIn(
            timesheet_entry.id,
            timesheets.ids,
            "Portal user should not see the timesheet when not assigned as the task's partner.",
        )

        self.project_cows.write({"partner_id": self.user_portal.partner_id.id})
        timesheets = AnalyticLineModel.search(timesheet_domain)
        self.assertIn(
            timesheet_entry.id,
            timesheets.ids,
            "Portal user should see the timesheet when set as the project’s partner.",
        )
