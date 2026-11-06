# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseTierValidation(TransactionCase):
    """ตรวจกลุ่ม CEO และการตั้งค่า tier.definition ของค่าใช้จ่าย"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.product = cls.env["product.product"].create({
            "name": "Tier Test Expense",
            "type": "service",
        })
        cls.employee = cls.env["hr.employee"].search([], limit=1)
        if not cls.employee:
            cls.employee = cls.env["hr.employee"].create({"name": "Tier Test Employee"})

    def _make_user(self, login, group_xmlids):
        groups = [self.env.ref(x).id for x in group_xmlids]
        groups.append(self.env.ref("base.group_user").id)
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "group_ids": [Command.set(sorted(set(groups)))],
        })

    def test_ceo_group_exists(self):
        """ต้องมีกลุ่ม Expense CEO Approver"""
        group = self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver")
        self.assertEqual(group.name, "Expense CEO Approver")

    def _expense_tier_definitions(self):
        return self.env["tier.definition"].search([
            ("model_id.model", "=", "hr.expense"),
            ("company_id", "=", False),
        ])

    def test_three_tier_definitions_exist(self):
        """ต้องมี tier.definition 3 รายการสำหรับ hr.expense"""
        defs = self._expense_tier_definitions()
        self.assertEqual(len(defs), 3)

    def test_tier_definitions_reviewer_groups(self):
        """ชั้น 1 = HR Expense Manager, ชั้น 2 = Account Manager, ชั้น 3 = CEO"""
        defs = self._expense_tier_definitions()
        groups = defs.mapped("reviewer_group_id")
        self.assertIn(self.env.ref("hr_expense.group_hr_expense_manager"), groups)
        self.assertIn(self.env.ref("account.group_account_manager"), groups)
        self.assertIn(
            self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver"),
            groups,
        )

    def test_tier_definition_order_and_forward(self):
        """ชั้น 1 มี sequence สูงสุด และทุกชั้นเปิด Forward + approve_sequence"""
        defs = self._expense_tier_definitions().sorted("sequence", reverse=True)
        self.assertEqual(defs.mapped("sequence"), [30, 20, 10])
        self.assertEqual(defs[0].reviewer_group_id,
                         self.env.ref("hr_expense.group_hr_expense_manager"))
        self.assertEqual(defs[1].reviewer_group_id,
                         self.env.ref("account.group_account_manager"))
        self.assertEqual(defs[2].reviewer_group_id,
                         self.env.ref("od19_hr_expense_thai.group_od19_expense_ceo_approver"))
        self.assertTrue(all(defs.mapped("approve_sequence")))
        self.assertTrue(all(defs.mapped("has_forward")))

    def _submitted_expense(self, amount=1500.0):
        expense = self.env["hr.expense"].create({
            "name": "Tier Flow Expense",
            "product_id": self.product.id,
            "total_amount": amount,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
        })
        # เซ็ตตรง ๆ เพื่อเลี่ยง auto-validation ของ core (_can_be_autovalidated)
        expense.approval_state = "submitted"
        return expense

    def test_request_validation_creates_three_reviews(self):
        """การขออนุมัติต้องสร้าง review 3 รายการ เรียงตามลำดับชั้น"""
        expense = self._submitted_expense()
        expense.request_validation()
        self.assertEqual(len(expense.review_ids), 3)
        self.assertEqual(
            expense.review_ids.sorted("sequence").mapped("sequence"), [1, 2, 3]
        )
        # engine เลื่อน review ลำดับต่ำสุด (ชั้น 1) เป็น ``pending`` ทันที
        # (tier_review._update_review_status) ส่วนชั้นถัดไปยังเป็น ``waiting``
        self.assertEqual(
            expense.review_ids.sorted("sequence").mapped("status"),
            ["pending", "waiting", "waiting"],
        )
        self.assertEqual(expense.validation_status, "pending")

    def test_cannot_approve_out_of_order(self):
        """CEO อนุมัติก่อนลำดับไม่ได้: ต้องหยุดที่ review แรกที่ไม่ใช่ของตน"""
        ceo = self._make_user(
            "tier_ceo", ["od19_hr_expense_thai.group_od19_expense_ceo_approver"]
        )
        expense = self._submitted_expense()
        expense.request_validation()
        expense.with_user(ceo).validate_tier()
        # CEO ไม่ใช่ผู้รับผิดชอบ review ลำดับต้น จึงไม่มีการอนุมัติเกิดขึ้น
        self.assertIn(expense.validation_status, ("pending", "waiting"))
        self.assertEqual(expense.approval_state, "submitted")

    def test_full_three_level_approval_flow(self):
        """อนุมัติครบ 3 ชั้นตามลำดับ แล้ว validation_status = validated"""
        manager = self._make_user(
            "tier_manager", ["hr_expense.group_hr_expense_manager"]
        )
        accountant = self._make_user(
            "tier_accountant", ["account.group_account_manager"]
        )
        ceo = self._make_user(
            "tier_ceo2", ["od19_hr_expense_thai.group_od19_expense_ceo_approver"]
        )
        expense = self._submitted_expense()
        expense.request_validation()

        # ระหว่างทางชั้นถัดไปยังเป็น ``waiting`` จนกว่าผู้ตรวจชั้นนั้นจะอนุมัติ
        # จึงยอมรับทั้ง pending/waiting (ไม่ผูกกับ ``pending`` ตายตัว)
        expense.with_user(manager).validate_tier()
        self.assertIn(expense.validation_status, ("pending", "waiting"))

        expense.with_user(accountant).validate_tier()
        self.assertIn(expense.validation_status, ("pending", "waiting"))

        expense.with_user(ceo).validate_tier()
        self.assertEqual(expense.validation_status, "validated")

    def test_write_blocked_while_under_validation(self):
        """ห้ามแก้ไขเอกสารระหว่างอยู่ภายใต้การอนุมัติ"""
        expense = self._submitted_expense()
        expense.request_validation()
        with self.assertRaises(ValidationError):
            expense.write({"name": "Hacked"})
