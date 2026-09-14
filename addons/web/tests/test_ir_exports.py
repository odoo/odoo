from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged("post_install", "-at_install", "web_export")
class TestIrExportsLineAcl(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.export_group = cls.env.ref("base.group_allow_export")
        cls.user_demo.write({"group_ids": [Command.unlink(cls.export_group.id)]})
        cls.user_exporter = cls.env["res.users"].create(
            {
                "name": "Exporter",
                "login": "exporter_iexp_l1",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(cls.export_group.id),
                ],
            }
        )
        cls.preset = cls.env["ir.exports"].create(
            {"name": "preset", "resource": "res.partner"}
        )

    def test_non_export_user_cannot_create_line(self):
        with self.assertRaises(AccessError):
            self.env["ir.exports.line"].with_user(self.user_demo).create(
                {"name": "name", "export_id": self.preset.id}
            )

    def test_non_export_user_cannot_write_line(self):
        line = self.env["ir.exports.line"].create(
            {"name": "name", "export_id": self.preset.id}
        )
        with self.assertRaises(AccessError):
            line.with_user(self.user_demo).write({"name": "other"})

    def test_non_export_user_cannot_unlink_line(self):
        line = self.env["ir.exports.line"].create(
            {"name": "name", "export_id": self.preset.id}
        )
        with self.assertRaises(AccessError):
            line.with_user(self.user_demo).unlink()

    def test_export_user_can_crud_line(self):
        Line = self.env["ir.exports.line"].with_user(self.user_exporter)
        line = Line.create({"name": "name", "export_id": self.preset.id})
        self.assertTrue(line)
        line.write({"name": "renamed"})
        self.assertEqual(line.name, "renamed")
        line.unlink()
        self.assertFalse(line.exists())
