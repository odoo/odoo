from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockSms(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.Picking = cls.env["stock.picking"]

    def test_default_confirmation_template_is_delivery_template(self):
        expected = self.env.ref("stock_sms.sms_template_data_stock_delivery")
        self.assertEqual(
            self.company._default_stock_sms_confirmation_template_id(), expected.id
        )

    def test_get_pickings_to_warn_sms_is_disabled_during_tests(self):
        self.assertFalse(self.Picking._get_pickings_to_warn_sms())

    def test_generate_warn_sms_wizard_opens_confirmation(self):
        action = self.Picking._action_generate_warn_sms_wizard()
        self.assertEqual(action["res_model"], "confirm.stock.sms")
        self.assertEqual(action["target"], "new")
        self.assertTrue(action["res_id"])
