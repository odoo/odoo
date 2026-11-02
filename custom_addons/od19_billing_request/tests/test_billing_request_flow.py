from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.od19_ar_require_evidence = False
        cls.product = cls.env["product.product"].create(
            {"name": "Flow Item", "type": "service", "list_price": 10.0}
        )
        cls.accounting_user = cls.env["res.users"].create(
            {
                "name": "BR Accountant",
                "login": "br_accountant",
                "group_ids": [
                    (4, cls.env.ref("od19_billing_request.group_od19_billing_accounting").id)
                ],
            }
        )

    def _draft_request(self):
        return self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "line_ids": [
                    (0, 0, {"product_id": self.product.id, "quantity": 1.0})
                ],
            }
        )

    def test_submit_without_lines_is_blocked(self):
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        with self.assertRaises(UserError):
            request.action_submit()

    def test_submit_sets_state_and_notifies_accounting(self):
        request = self._draft_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "od19.billing.request"),
                ("res_id", "=", request.id),
                ("user_id", "=", self.accounting_user.id),
            ]
        )
        self.assertTrue(activities)

    def test_reject_then_reset(self):
        request = self._draft_request()
        request.action_submit()
        request.action_reject()
        request.reject_reason = "เอกสารไม่ครบ"
        self.assertEqual(request.state, "rejected")
        request.action_reset_draft()
        self.assertEqual(request.state, "draft")

    def test_cancel(self):
        request = self._draft_request()
        request.action_cancel()
        self.assertEqual(request.state, "cancelled")
