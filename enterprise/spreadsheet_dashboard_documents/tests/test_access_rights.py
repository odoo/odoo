from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user

class TestDashboardDocumentsAccesss(TransactionCase):

    def test_dashboard_comments_access(self):
        internal_user = new_test_user(self.env, "Bob", groups="base.group_user")
        dashboard_group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "spreadsheet_data": r"{}",
                "group_ids": [Command.set(self.env.ref("base.group_system").ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        comments_thread = self.env["spreadsheet.cell.thread"].create({
            "dashboard_id": dashboard.id,
        })
        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).read(["message_ids"])

        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).message_post(body="Hello there!")

        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).unlink()

        with self.assertRaises(AccessError):
            self.env["spreadsheet.cell.thread"].with_user(internal_user).create({
            "dashboard_id": dashboard.id,
        })

    def test_create_comment_on_accessible_dashboard(self):
        internal_user = new_test_user(self.env, "Bob", groups="base.group_user")
        dashboard_group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "spreadsheet_data": r"{}",
                "group_ids": [Command.set(self.env.ref("base.group_user").ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        self.env["spreadsheet.cell.thread"].with_user(internal_user).create({
            "dashboard_id": dashboard.id,
        })

    def test_document_comments_access(self):
        internal_user = new_test_user(self.env, "Bob", groups="base.group_user")
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": r"{}",
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        comments_thread = self.env["spreadsheet.cell.thread"].create({
            "document_id": document.id,
        })
        self.assertTrue(comments_thread.with_user(internal_user).read(["message_ids"]), "The internal user can access messages.")

        self.assertTrue(comments_thread.with_user(internal_user).message_post(body="Hello there!"), "The internal user can post messages.")

        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).unlink()

        self.assertTrue(self.env["spreadsheet.cell.thread"].with_user(internal_user).create({"document_id": document.id,}), "The internal user can create the thread.")

    def test_spreadsheet_template_comments_access(self):
        internal_user = new_test_user(self.env, "Bob", groups="base.group_user")
        template = self.env["spreadsheet.template"].create({
            "spreadsheet_data": r"{}",
            "name": "Template name",
        })
        comments_thread = self.env["spreadsheet.cell.thread"].create({
            "template_id": template.id,
        })
        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).read(["message_ids"])

        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).message_post(body="Hello there!")

        with self.assertRaises(AccessError):
            comments_thread.with_user(internal_user).unlink()

        with self.assertRaises(AccessError):
            self.env["spreadsheet.cell.thread"].with_user(internal_user).create({
            "template_id": template.id,
        })
