from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteSms(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        Visitor = cls.env["website.visitor"]
        cls.partner_phone = Partner.create(
            {
                "name": "Reachable",
                "phone_ids": [
                    Command.create({"number": "+52 55 1234 5678", "type": "landline"})
                ],
            }
        )
        cls.partner_no_phone = Partner.create({"name": "Unreachable"})
        cls.visitor_phone = Visitor.create({"access_token": str(cls.partner_phone.id)})
        cls.visitor_no_phone = Visitor.create(
            {"access_token": str(cls.partner_no_phone.id)}
        )

    def test_can_use_sms_composer_follows_partner_phone(self):
        self.assertTrue(self.visitor_phone._can_use_sms_composer())
        self.assertFalse(self.visitor_no_phone._can_use_sms_composer())

    def test_action_send_sms_without_phone_raises(self):
        with self.assertRaises(UserError):
            self.visitor_no_phone.action_send_sms()

    def test_action_send_sms_opens_composer_for_partner(self):
        action = self.visitor_phone.action_send_sms()
        self.assertEqual(action["res_model"], "sms.composer")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_res_id"], self.partner_phone.id)
        self.assertEqual(action["context"]["default_number_field_name"], "phone_ids")

    def test_prepare_sms_composer_context(self):
        ctx = self.visitor_phone._prepare_sms_composer_context()
        self.assertEqual(ctx["default_res_model"], "res.partner")
        self.assertEqual(ctx["default_res_id"], self.partner_phone.id)
        self.assertEqual(ctx["default_composition_mode"], "comment")
        self.assertEqual(ctx["default_number_field_name"], "phone_ids")
