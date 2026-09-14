from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "web_report")
class TestReportLayoutAccess(TransactionCase):
    def test_internal_user_cannot_modify_report_layout(self):
        user = new_test_user(self.env, login="rl_plain_user")
        view = self.env["ir.ui.view"].search([], limit=1)
        layout = (
            self.env["report.layout"]
            .sudo()
            .create({"name": "audit layout", "view_id": view.id})
        )

        layout.with_user(user).read(["name"])

        with self.assertRaises(AccessError):
            self.env["report.layout"].with_user(user).create(
                {"name": "x", "view_id": view.id}
            )
        with self.assertRaises(AccessError):
            layout.with_user(user).write({"name": "hacked"})
        with self.assertRaises(AccessError):
            layout.with_user(user).unlink()

    def test_system_user_can_modify_report_layout(self):
        admin = new_test_user(self.env, login="rl_sys_user", groups="base.group_system")
        view = self.env["ir.ui.view"].search([], limit=1)
        layout = (
            self.env["report.layout"]
            .with_user(admin)
            .create({"name": "sys layout", "view_id": view.id})
        )
        layout.write({"name": "sys layout 2"})
        layout.unlink()


@tagged("post_install", "-at_install", "web_report")
class TestReportLayoutCascade(TransactionCase):
    def test_view_unlink_cascades_to_layout(self):
        view = (
            self.env["ir.ui.view"]
            .sudo()
            .create(
                {
                    "name": "audit cascade template",
                    "type": "qweb",
                    "arch": "<t t-name='audit_cascade'><div/></t>",
                }
            )
        )
        layout = (
            self.env["report.layout"]
            .sudo()
            .create({"name": "audit cascade layout", "view_id": view.id})
        )
        self.assertTrue(layout.exists())

        view.unlink()
        self.assertFalse(
            layout.exists(),
            "report.layout must be cascade-deleted when its view_id is removed",
        )
