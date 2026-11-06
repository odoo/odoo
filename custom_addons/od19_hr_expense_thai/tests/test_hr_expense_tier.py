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
