from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestViews(TransactionCase):
    def test_form_view_loads(self):
        view = self.env.ref("od19_billing_request.view_od19_billing_request_form")
        self.assertTrue(view)

    def test_billing_queue_action_filters_submitted(self):
        action = self.env.ref(
            "od19_billing_request.action_od19_billing_request_queue"
        )
        self.assertIn("submitted", action.domain)

    def test_menus_exist(self):
        self.assertTrue(
            self.env.ref("od19_billing_request.menu_od19_billing_request_root")
        )
        self.assertTrue(
            self.env.ref("od19_billing_request.menu_od19_billing_request_queue")
        )
