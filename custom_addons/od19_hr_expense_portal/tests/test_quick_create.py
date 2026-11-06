# -*- coding: utf-8 -*-
"""Tests for the quick expense submission wizard."""

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestQuickCreate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.user = cls.env["res.users"].create({
            "name": "Wizard User",
            "login": "od19_wizard_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Wizard Employee",
            "user_id": cls.user.id,
        })
        cls.category = cls.env["product.product"].create({
            "name": "Wizard plain category",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })
        cls.mileage_category = cls.env["product.product"].create({
            "name": "Wizard mileage category",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
            "od19_is_mileage_category": True,
        })

    def _wizard(self, **vals):
        base = {
            "employee_id": self.employee.id,
            "submit_now": False,
        }
        base.update(vals)
        return self.env["od19.expense.quick.create"].with_user(
            self.user).create(base)

    def test_plain_expense_created(self):
        wiz = self._wizard(expense_category_id=self.category.id, amount=250.0)
        self.assertFalse(wiz.od19_is_mileage)
        action = wiz.action_create_expense()
        expense = self.env["hr.expense"].browse(action["res_id"])
        self.assertEqual(expense.total_amount, 250.0)
        self.assertEqual(expense.employee_id, self.employee)
        self.assertEqual(expense.product_id, self.category)
        self.assertEqual(expense.state, "draft")

    def test_mileage_expense_created(self):
        wiz = self._wizard(
            expense_category_id=self.mileage_category.id, distance_km=20.0)
        self.assertTrue(wiz.od19_is_mileage)
        self.assertEqual(wiz.total_amount, 100.0)
        action = wiz.action_create_expense()
        expense = self.env["hr.expense"].browse(action["res_id"])
        self.assertTrue(expense.od19_is_mileage)
        self.assertEqual(expense.quantity, 20.0)
        self.assertEqual(expense.total_amount, 100.0)
        self.assertEqual(expense.price_unit, 5.0)

    def test_submit_now_submits(self):
        wiz = self._wizard(
            expense_category_id=self.category.id, amount=100.0, submit_now=True)
        action = wiz.action_create_expense()
        expense = self.env["hr.expense"].browse(action["res_id"])
        self.assertNotEqual(expense.state, "draft")
