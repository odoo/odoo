from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("mail_tools", "-at_install", "post_install")
class TestIrModelMail(TransactionCase):
    def test_unlinking_a_custom_model_removes_its_attachments_url_ones_included(self):
        model = self.env["ir.model"].create(
            {"name": "Gone Model", "model": "x_mail_gone", "state": "manual"}
        )
        Attachment = self.env["ir.attachment"]
        Attachment.create(
            [
                {
                    "name": "link",
                    "type": "url",
                    "url": "https://example.com/doc",
                    "res_model": "x_mail_gone",
                    "res_id": 0,
                },
                {"name": "blob", "raw": b"stored bytes", "res_model": "x_mail_gone"},
            ]
        )
        self.assertEqual(
            Attachment.search_count([("res_model", "=", "x_mail_gone")]), 2
        )

        model.unlink()

        self.assertFalse(Attachment.search([("res_model", "=", "x_mail_gone")]))
        self.assertNotIn("x_mail_gone", self.env)

    def test_both_definition_readers_annotate_alike(self):
        IrModel = self.env["ir.model"]
        by_name = IrModel._get_definitions(["res.partner"])["res.partner"]
        by_fetch = IrModel._get_model_definitions(["res.partner"])["res.partner"]
        for definition in (by_name, by_fetch):
            self.assertTrue(definition["has_activities"])
            self.assertTrue(definition["fields"]["email"]["tracking"])
            self.assertNotIn("tracking", definition["fields"]["comment"])

    def test_a_custom_thread_model_reflects_its_mixins_without_a_false_module(self):
        model = self.env["ir.model"].create(
            {
                "name": "Threaded Custom",
                "model": "x_mail_threaded",
                "state": "manual",
                "is_mail_thread": True,
                "is_mail_activity": True,
            }
        )
        inherits = self.env["ir.model.inherit"].search([("model_id", "=", model.id)])
        self.assertIn("mixin.mail.thread", inherits.parent_id.mapped("model"))
        self.assertIn(
            "mixin.mail.activity",
            inherits.parent_id.mapped("model"),
            "only the custom class links this mixin, and it has no module",
        )
        self.assertFalse(
            self.env["ir.model.data"].search_count([("module", "=", "False")])
        )
