# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPayableUatBusinessFlow(AccountTestInvoicingCommon):
    """P1-T10 — UAT จำลอง business flow ฝั่งเจ้าหนี้.

    Child spec: W2-PAYABLE-CONTROL-GATE
    ``docs/superpowers/specs/2026-11-01-od19-payable-control-gate-design.md`` (§11 P1-T10).

    หลักฐาน UAT ที่รันได้จริง (13 เคส) จำลองวงจร
    **PO → รับของ → บิล → เตรียมจ่าย → อนุมัติ → จ่าย** ครบทุกข้อบังคับของฝั่งเจ้าหนี้
    และเทียบผลกับ gate จริงทุกตัว:

    * 3-way / 2-way match (``product.purchase_method``),
    * bill-first (``od19_require_vendor_bill_for_payment``),
    * Prepare→Approve (``od19_enforce_prepare_approval``),
    * Segregation of Duties (``od19_enforce_prepare_sod``),
    * override พร้อมเหตุผล, Block Payment และ Group Payments.
    """

    @classmethod
    def get_default_groups(cls):
        # ``AccountTestInvoicingCommon`` runs the class with an independent
        # accounting user that has no HR groups. Validating a receipt goes
        # through ``stock.picking``, whose label module resolves a department
        # from the current user's ``hr.employee`` record, so the HR user group
        # (which owns the ``hr.department`` / ``resource.resource`` create
        # rights) must be added to the test user.
        no_group = cls.env["res.groups"].browse()
        return super().get_default_groups() | (
            cls.env.ref("hr.group_hr_user", False) or no_group
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.vendor = cls.env["res.partner"].create(
            {"name": "UAT Vendor", "company_type": "company"}
        )
        cls.goods = cls.env["product.product"].create(
            {
                "name": "UAT Goods",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.service = cls.env["product.product"].create(
            {"name": "UAT Service", "purchase_ok": True, "type": "service"}
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]
        # การยืนยันรับของผ่าน stock.picking (label module) ต้องมีพนักงานที่มีรหัสแผนก
        cls.department = cls.env["hr.department"].create(
            {"name": "UAT Operations", "code": "UATOPS"}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "UAT Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.manager = cls._uat_user(
            "uat.purchase.manager",
            ["base.group_user", "purchase.group_purchase_manager"],
        )
        cls.maker = cls._uat_user(
            "uat.ap.maker", ["base.group_user", "account.group_account_invoice"]
        )
        cls.approver = cls._uat_user(
            "uat.ap.approver",
            [
                "base.group_user",
                "account.group_account_invoice",
                "od19_accounting_payment_voucher_reports.group_od19_payment_approver",
            ],
        )

    @classmethod
    def _uat_user(cls, login, group_xmlids):
        """สร้างผู้ใช้ภายในที่มีเฉพาะกลุ่มที่กำหนด (สำหรับทดสอบ SoD)."""
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [
                    Command.set([cls.env.ref(xmlid).id for xmlid in group_xmlids])
                ],
            }
        )

    # ------------------------------------------------------------------
    # Helpers — จำลองขั้นตอนธุรกิจ
    # ------------------------------------------------------------------
    def _po(self, product, qty, price_unit=100.0):
        """สร้างใบสั่งซื้อ → ขออนุมัติ → อนุมัติ → ยืนยัน (Commit)."""
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": product.display_name,
                "product_id": product.id,
                "product_qty": qty,
                "price_unit": price_unit,
                "product_uom_id": product.uom_id.id,
                "date_planned": "2016-01-01 00:00:00",
            }
        )
        order.action_od19_submit_for_approval()
        order.with_user(self.manager).action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        return order

    def _receive(self, order, qty):
        """ยืนยันรับของตามจำนวนที่กำหนด."""
        picking = order.picking_ids.filtered(lambda p: p.state != "done")
        picking.move_ids.quantity = qty
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        order.invalidate_recordset(["receipt_status"])

    def _bill_from_po(self, order):
        """ออกใบตั้งหนี้จาก PO → ใส่เลขใบกำกับภาษี → Post."""
        order.action_create_invoice()
        bill = order.invoice_ids[:1]
        bill.invoice_date = "2016-01-01"
        bill.tax_invoice_ids.write(
            {
                "tax_invoice_number": "UAT-TINV-%s" % bill.id,
                "tax_invoice_date": "2016-01-01",
            }
        )
        bill.action_post()
        return bill

    def _register(self, bills, prepare=False, group_payment=True, **overrides):
        """เรียก "ชำระเงิน" (Register Payment) จากบิล."""
        vals = {
            "group_payment": group_payment,
            "od19_prepare_payment": prepare,
            "payment_date": "2016-01-01",
        }
        vals.update(overrides)
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bills.ids)
            .create(vals)
            ._create_payments()
        )

    def _manual_payment(self, **overrides):
        """สร้างรายการจ่ายตรง (ไม่ผ่านใบตั้งหนี้) เพื่อทดสอบ gate."""
        vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.vendor.id,
            "amount": 1000.0,
            "journal_id": self.bank_journal.id,
            "date": "2016-01-01",
        }
        vals.update(overrides)
        return self.env["account.payment"].create(vals)

    def _force_prepared(self, payment, user):
        payment.write(
            {"od19_prepare_state": "prepared", "od19_prepared_by": user.id}
        )

    # ------------------------------------------------------------------
    # เคส 1 — วงจรเต็ม (Critical Path)
    # ------------------------------------------------------------------
    def test_uat_01_full_flow_goods_prepare_approve_pay(self):
        """PO สินค้า → รับของ 10/10 → บิล → เตรียมจ่าย → อนุมัติ → จ่าย."""
        self.company.od19_require_vendor_bill_for_payment = True
        self.company.od19_enforce_prepare_approval = True

        order = self._po(self.goods, 10, 100.0)
        self._receive(order, 10)
        self.assertEqual(order.order_line.qty_received, 10.0)

        bill = self._bill_from_po(order)
        # The test company uses the generic chart of accounts, whose default
        # purchase tax (15%) applies on top of the ordered amount, so compare
        # the untaxed total with the PO value.
        self.assertEqual(bill.amount_untaxed, 1000.0)

        payment = self._register(bill, prepare=True)
        self.assertEqual(payment.state, "draft")
        self.assertEqual(payment.od19_prepare_state, "draft")

        # ยังไม่อนุมัติ → ยืนยันรายการจ่ายไม่ได้
        with self.assertRaisesRegex(UserError, "ยังไม่ผ่านการอนุมัติ"):
            payment.action_post()

        payment.action_od19_prepare()
        self.assertEqual(payment.od19_prepare_state, "prepared")
        self.assertTrue(payment.od19_voucher_no.startswith("PV"))

        payment.action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")

        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(bill.payment_state, "paid")
        order.invalidate_recordset(["od19_vendor_bill_closure_state"])
        self.assertEqual(order.od19_vendor_bill_closure_state, "paid")

    # ------------------------------------------------------------------
    # เคส 2–4 — Three-way / Two-way match
    # ------------------------------------------------------------------
    def test_uat_02_goods_not_billable_before_receipt(self):
        """ของยังไม่รับ → ออกบิลไม่ได้ (3-way match)."""
        order = self._po(self.goods, 10, 100.0)
        self.assertEqual(order.order_line.qty_received, 0.0)
        self.assertEqual(order.order_line.qty_to_invoice, 0.0)
        self.assertEqual(order.invoice_status, "no")

    def test_uat_03_goods_bill_limited_to_received_quantity(self):
        """รับของ 6/10 → ออกบิลได้แค่ 6 (ส่วนที่เหลือยังออกบิลไม่ได้)."""
        order = self._po(self.goods, 10, 100.0)
        self._receive(order, 6)
        self.assertEqual(order.order_line.qty_received, 6.0)
        self.assertEqual(order.order_line.qty_to_invoice, 6.0)

        bill = self._bill_from_po(order)
        self.assertEqual(bill.invoice_line_ids.quantity, 6.0)
        self.assertEqual(order.order_line.qty_to_invoice, 0.0)
        self.assertEqual(order.order_line.qty_received, 6.0)
        self.assertEqual(order.invoice_status, "invoiced")

    def test_uat_04_service_two_way_match_bills_without_receipt(self):
        """บริการ (2-way match) → ออกบิลตามจำนวนสั่งได้เลย ไม่รอรับของ."""
        order = self._po(self.service, 3, 200.0)
        self.assertEqual(order.order_line.qty_to_invoice, 3.0)
        bill = self._bill_from_po(order)
        self.assertEqual(bill.amount_untaxed, 600.0)

    # ------------------------------------------------------------------
    # เคส 5–6 — Bill-first gate (AP bill-first rule)
    # ------------------------------------------------------------------
    def test_uat_05_bill_first_gate_blocks_payment_without_bill(self):
        """จ่ายเจ้าหนี้โดยไม่มีการตั้งหนี้ → ถูกบล็อก."""
        self.company.od19_require_vendor_bill_for_payment = True
        self.company.od19_enforce_prepare_approval = False
        payment = self._manual_payment()
        with self.assertRaisesRegex(UserError, "ไม่พบการตั้งหนี้"):
            payment.action_post()
        self.assertEqual(payment.state, "draft")

    def test_uat_06_payment_from_bill_passes_bill_first_gate(self):
        """จ่ายจากใบตั้งหนี้ที่ post แล้ว → ผ่านประตู bill-first."""
        self.company.od19_require_vendor_bill_for_payment = True
        order = self._po(self.service, 1, 300.0)
        bill = self._bill_from_po(order)
        payment = self._register(bill)
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(bill.payment_state, "paid")

    # ------------------------------------------------------------------
    # เคส 7–8 — Prepare→Approve gate
    # ------------------------------------------------------------------
    def test_uat_07_prepare_approve_gate_blocks_post(self):
        """บังคับใช้ Prepare→Approve → Post ก่อนอนุมัติถูกบล็อก."""
        self.company.od19_require_vendor_bill_for_payment = False
        self.company.od19_enforce_prepare_approval = True
        payment = self._manual_payment()
        with self.assertRaisesRegex(UserError, "ยังไม่ผ่านการอนุมัติ"):
            payment.action_post()
        self.assertEqual(payment.state, "draft")

    def test_uat_08_prepare_then_approve_then_post(self):
        """ทำครบ Prepare → Approve → Post สำเร็จ พร้อมร่องรอยผู้จัดทำ/ผู้อนุมัติ."""
        self.company.od19_require_vendor_bill_for_payment = False
        self.company.od19_enforce_prepare_approval = True
        payment = self._manual_payment()

        payment.action_od19_prepare()
        self.assertEqual(payment.od19_prepare_state, "prepared")
        self.assertTrue(payment.od19_voucher_no.startswith("PV"))

        payment.action_od19_approve()
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(payment.od19_prepared_by, self.env.user)
        self.assertEqual(payment.od19_approved_by, self.env.user)

    # ------------------------------------------------------------------
    # เคส 9–10 — Segregation of Duties
    # ------------------------------------------------------------------
    def test_uat_09_sod_blocks_self_approval(self):
        """ผู้จัดทำอนุมัติรายการที่ตัวเองจัดทำ → ถูกบล็อก (SoD)."""
        self.company.od19_require_vendor_bill_for_payment = False
        self.company.od19_enforce_prepare_sod = True
        payment = self._manual_payment()
        self._force_prepared(payment, self.maker)
        with self.assertRaisesRegex(UserError, "แยกหน้าที่"):
            payment.with_user(self.maker).action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "prepared")

    def test_uat_10_sod_allows_independent_approver(self):
        """ผู้อนุมัติคนละคนกับผู้จัดทำ → อนุมัติผ่าน."""
        self.company.od19_require_vendor_bill_for_payment = False
        self.company.od19_enforce_prepare_sod = True
        payment = self._manual_payment()
        self._force_prepared(payment, self.maker)
        payment.with_user(self.approver).action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")
        self.assertEqual(payment.od19_approved_by, self.approver)

    # ------------------------------------------------------------------
    # เคส 11 — Override (ข้ามการอนุมัติ)
    # ------------------------------------------------------------------
    def test_uat_11_override_requires_reason_and_allows_post(self):
        """ข้ามการอนุมัติ: ต้องมีเหตุผล และ Post ผ่านพร้อมร่องรอย."""
        self.company.od19_require_vendor_bill_for_payment = False
        self.company.od19_enforce_prepare_approval = True
        payment = self._manual_payment()

        with self.assertRaisesRegex(UserError, "เหตุผล"):
            payment.action_od19_override()

        payment.od19_override_reason = "จ่ายเร่งด่วนตามคำสั่งผู้บริหาร"
        payment.action_od19_override()
        self.assertTrue(payment.od19_approval_override)
        self.assertEqual(payment.od19_override_by, self.env.user)

        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))

    # ------------------------------------------------------------------
    # เคส 12 — Block Payment
    # ------------------------------------------------------------------
    def test_uat_12_blocked_bill_excluded_from_payment_run(self):
        """บิลที่ถูก Block ต้องไม่เข้าชุดสั่งจ่าย จนกว่าจะปลดบล็อก."""
        self.company.od19_require_vendor_bill_for_payment = False
        order = self._po(self.service, 1, 400.0)
        bill = self._bill_from_po(order)

        bill.action_toggle_block_payment()
        self.assertEqual(bill.payment_state, "blocked")
        with self.assertRaisesRegex(UserError, "blocked invoices"):
            bill.action_force_register_payment()

        bill.action_toggle_block_payment()  # ปลดบล็อกหลังตรวจสอบ
        payment = self._register(bill)
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(bill.payment_state, "paid")

    # ------------------------------------------------------------------
    # เคส 13 — Group Payments
    # ------------------------------------------------------------------
    def test_uat_13_group_payments_merge_same_vendor_bills(self):
        """รวมบิลเจ้าหนี้รายเดียวกันเป็นรายการจ่ายเดียว (Group Payments)."""
        self.company.od19_require_vendor_bill_for_payment = True
        first = self._bill_from_po(self._po(self.service, 1, 300.0))
        second = self._bill_from_po(self._po(self.service, 1, 200.0))

        payments = self._register(first + second, group_payment=True)
        self.assertEqual(len(payments), 1)
        self.assertAlmostEqual(
            payments.amount, first.amount_total + second.amount_total
        )
        self.assertEqual(set((first + second).mapped("payment_state")), {"paid"})
