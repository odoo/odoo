# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
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

    def _create_gate_user(self, login, group_xmlids):
        """Create an internal user with exactly the given groups."""
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [
                    Command.set([self.env.ref(xmlid).id for xmlid in group_xmlids])
                ],
            }
        )

    def _force_prepared(self, payment, prepared_by):
        """Set the payment to "prepared" as if ``prepared_by`` had done it."""
        payment.write(
            {
                "od19_prepare_state": "prepared",
                "od19_prepared_by": prepared_by.id,
            }
        )

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

    # ------------------------------------------------------------------
    # T4 — override + audit
    # ------------------------------------------------------------------
    def test_override_requires_reason(self):
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment()
        with self.assertRaisesRegex(UserError, "เหตุผล"):
            payment.action_od19_override()
        self.assertFalse(payment.od19_approval_override)

    def test_override_allows_post(self):
        self.env.company.od19_enforce_prepare_approval = True
        payment = self._create_payment()
        payment.od19_override_reason = "จ่ายเร่งด่วนตามคำสั่งผู้บริหาร"
        payment.action_od19_override()
        self.assertTrue(payment.od19_approval_override)
        self.assertEqual(payment.od19_override_by, self.env.user)
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))

    def test_override_records_mail_message(self):
        payment = self._create_payment()
        payment.od19_override_reason = "urgent payment per management order"
        payment.action_od19_override()
        bodies = " ".join(payment.message_ids.mapped("body"))
        self.assertIn("Approval Override", bodies)

    def test_override_denied_for_non_approver(self):
        clerk = self._create_gate_user("gate_clerk_ovr", ["account.group_account_invoice"])
        payment = self._create_payment()
        payment.od19_override_reason = "x"
        with self.assertRaisesRegex(UserError, "เฉพาะผู้อนุมัติ"):
            payment.with_user(clerk).action_od19_override()

    # ------------------------------------------------------------------
    # T5 — segregation of duties
    # ------------------------------------------------------------------
    def test_sod_blocks_self_approval(self):
        self.env.company.od19_enforce_prepare_sod = True
        maker = self._create_gate_user("gate_maker_sod", ["account.group_account_invoice"])
        payment = self._create_payment()
        self._force_prepared(payment, maker)
        with self.assertRaisesRegex(UserError, "แยกหน้าที่"):
            payment.with_user(maker).action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "prepared")

    def test_sod_allows_different_approver(self):
        self.env.company.od19_enforce_prepare_sod = True
        maker = self._create_gate_user("gate_maker_sod2", ["account.group_account_invoice"])
        approver = self._create_gate_user(
            "gate_approver_sod2",
            [
                "account.group_account_invoice",
                "od19_accounting_payment_voucher_reports.group_od19_payment_approver",
            ],
        )
        payment = self._create_payment()
        self._force_prepared(payment, maker)
        payment.with_user(approver).action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")
        self.assertEqual(payment.od19_approved_by, approver)

    def test_sod_disabled_allows_self_approval(self):
        self.env.company.od19_enforce_prepare_sod = False
        maker = self._create_gate_user("gate_maker_sod3", ["account.group_account_invoice"])
        payment = self._create_payment()
        self._force_prepared(payment, maker)
        payment.with_user(maker).action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")

    def test_sod_bypassed_by_admin(self):
        self.env.company.od19_enforce_prepare_sod = True
        payment = self._create_payment()
        payment.action_od19_prepare()
        # ``self.env.user`` (admin/superuser) prepared it and can still approve.
        payment.action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")

    # ------------------------------------------------------------------
    # T6 — security groups
    # ------------------------------------------------------------------
    def test_payment_gate_groups_and_implications(self):
        approver = self.env.ref(
            "od19_accounting_payment_voucher_reports.group_od19_payment_approver"
        )
        admin = self.env.ref(
            "od19_accounting_payment_voucher_reports.group_od19_payment_admin"
        )
        self.assertIn(approver, admin.implied_ids)
        self.assertIn(self.env.ref("base.group_user"), approver.implied_ids)
        self.assertIn(
            self.env.ref("account.group_account_invoice"), approver.implied_ids
        )
        self.assertTrue(self.env.user.has_group(
            "od19_accounting_payment_voucher_reports.group_od19_payment_approver"
        ))
