# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestApBlockAndGroupPayments(AccountTestInvoicingCommon):
    """P1 (T8) — AP SOP: Block Payment + Group Payments.

    Child spec: W2-PAYABLE-CONTROL-GATE
    ``docs/superpowers/specs/2026-11-01-od19-payable-control-gate-design.md``
    (§5.6 Block Payment Gate / §5.7 Group Payments).

    These two CE-native controls are configuration + procedure, not new code, so
    the test pins the behaviour the AP SOP relies on:

    * ``account.move.action_toggle_block_payment`` freezes a bill (``blocked``)
      so the "Register Payment" button refuses it until the reviewer releases
      it again.
    * ``account.payment.register.group_payment`` merges several bills of the
      same vendor into a single payment (the CE replacement for the
      Enterprise-only batch payment file).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Keep the pre-existing AP bill-first rule out of the way so the
        # assertions below exercise Block/Group behaviour, not that gate.
        cls.env.company.od19_require_vendor_bill_for_payment = False

    def _bill(self, amount):
        return self._create_invoice_one_line(
            price_unit=amount,
            move_type="in_invoice",
            partner_id=self.partner_a,
            post=True,
        )

    def _register(self, bills, group_payment=True):
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bills.ids)
            .create({"group_payment": group_payment})
            ._create_payments()
        )

    # ------------------------------------------------------------------
    # §5.6 — Block Payment Gate
    # ------------------------------------------------------------------
    def test_block_payment_toggles_blocked_state(self):
        bill = self._bill(1000.0)
        self.assertEqual(bill.payment_state, "not_paid")
        bill.action_toggle_block_payment()
        self.assertEqual(bill.payment_state, "blocked")
        bill.action_toggle_block_payment()
        self.assertEqual(bill.payment_state, "not_paid")

    def test_blocked_bill_refuses_register_payment(self):
        bill = self._bill(1000.0)
        bill.action_toggle_block_payment()
        with self.assertRaisesRegex(UserError, "blocked invoices"):
            bill.action_force_register_payment()
        self.assertEqual(bill.payment_state, "blocked")

    def test_released_bill_can_be_paid(self):
        bill = self._bill(1000.0)
        bill.action_toggle_block_payment()
        bill.action_toggle_block_payment()  # review passed -> release
        payments = self._register(bill)
        self.assertEqual(len(payments), 1)
        self.assertEqual(bill.payment_state, "paid")

    # ------------------------------------------------------------------
    # §5.7 — Group Payments
    # ------------------------------------------------------------------
    def test_group_payments_merge_same_vendor_bills(self):
        bills = self._bill(1000.0) + self._bill(2000.0)
        payments = self._register(bills, group_payment=True)
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 3000.0)
        self.assertEqual(set(bills.mapped("payment_state")), {"paid"})

    def test_group_payment_disabled_creates_one_payment_per_bill(self):
        bills = self._bill(1000.0) + self._bill(2000.0)
        payments = self._register(bills, group_payment=False)
        self.assertEqual(len(payments), 2)

    def test_blocked_bill_kept_out_of_run_until_released(self):
        first = self._bill(1000.0)
        second = self._bill(2000.0)
        second.action_toggle_block_payment()
        # A blocked bill must not enter the payment run (SOP step 3).
        with self.assertRaisesRegex(UserError, "blocked invoices"):
            (first + second).action_force_register_payment()
        second.action_toggle_block_payment()  # released after review
        payments = self._register(first + second, group_payment=True)
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 3000.0)
