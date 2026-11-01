# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPayableControlGate(AccountTestInvoicingCommon):
    """P1 (T1-T3) — enforce Prepare -> Approve on vendor disbursements.

    Child spec: W2-PAYABLE-CONTROL-GATE
    ``docs/superpowers/specs/2026-11-01-od19-payable-control-gate-design.md``
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Isolate the Prepare/Approve gate from the existing AP bill-first rule
        # so the assertions below exercise our control, not the vendor-bill gate.
        cls.env.company.od19_require_vendor_bill_for_payment = False
        cls.journal = cls.company_data["default_journal_bank"]

    def _create_payment(self, **overrides):
        vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.partner_a.id,
            "amount": 1000.0,
            "journal_id": self.journal.id,
            "date": "2016-01-01",
        }
        vals.update(overrides)
        return self.env["account.payment"].create(vals)

    def _has_field(self, name):
        return name in self.env["account.payment"]._fields

    # ------------------------------------------------------------------
    # T1 — company settings (defaults: enforce=False, sod=True)
    # ------------------------------------------------------------------
    def test_settings_defaults(self):
        defaults = self.env["res.company"].default_get(
            ["od19_enforce_prepare_approval", "od19_enforce_prepare_sod"]
        )
        self.assertFalse(defaults.get("od19_enforce_prepare_approval", False))
        self.assertTrue(defaults.get("od19_enforce_prepare_sod"))

    def test_settings_are_read_from_company(self):
        self.env.company.od19_enforce_prepare_approval = True
        self.env.company.od19_enforce_prepare_sod = False
        settings = self.env["res.config.settings"].create(
            {"company_id": self.env.company.id}
        )
        self.assertTrue(settings.od19_enforce_prepare_approval)
        self.assertFalse(settings.od19_enforce_prepare_sod)

    # ------------------------------------------------------------------
    # T2 — _od19_requires_prepare_approval() allow-list
    # ------------------------------------------------------------------
    def test_hook_true_for_outbound_supplier(self):
        payment = self._create_payment()
        self.assertTrue(payment._od19_requires_prepare_approval())

    def test_hook_false_for_inbound_customer(self):
        payment = self._create_payment(
            payment_type="inbound", partner_type="customer"
        )
        self.assertFalse(payment._od19_requires_prepare_approval())

    def test_hook_false_for_outbound_customer(self):
        payment = self._create_payment(partner_type="customer")
        self.assertFalse(payment._od19_requires_prepare_approval())

    def test_hook_false_with_skip_context(self):
        payment = self._create_payment()
        self.assertFalse(
            payment.with_context(od19_skip_prepare_gate=True)
            ._od19_requires_prepare_approval()
        )

    def test_hook_false_for_expense_payment(self):
        if not self._has_field("od19_is_expense_payment"):
            self.skipTest("od19_is_expense_payment is not installed")
        payment = self._create_payment(od19_is_expense_payment=True)
        self.assertFalse(payment._od19_requires_prepare_approval())

    # ------------------------------------------------------------------
    # T3 — action_post() guard
    # ------------------------------------------------------------------
    def test_post_blocked_until_approved(self):
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment()
        with self.assertRaisesRegex(UserError, "ยังไม่ผ่านการอนุมัติ"):
            payment.action_post()
        self.assertEqual(payment.state, "draft")

    def test_post_passes_after_prepare_and_approve(self):
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment()
        payment.action_od19_prepare()
        payment.action_od19_approve()
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))

    def test_post_allowed_when_enforcement_disabled(self):
        self.env.company.od19_enforce_prepare_approval = False
        payment = self._create_payment()
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))

    def test_post_allowed_with_skip_context(self):
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment()
        payment.with_context(od19_skip_prepare_gate=True).action_post()
        self.assertIn(payment.state, ("in_process", "paid"))

    def test_expense_payment_posts_when_enforcement_on(self):
        if not self._has_field("od19_is_expense_payment"):
            self.skipTest("od19_is_expense_payment is not installed")
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment(od19_is_expense_payment=True)
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))
