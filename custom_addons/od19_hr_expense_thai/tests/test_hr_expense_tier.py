# -*- coding: utf-8 -*-
from odoo import Command
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
