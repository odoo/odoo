# -*- coding: utf-8 -*-
"""Tests for mileage reimbursement (ค่าเดินทางตามระยะทาง) - T9/T10.

Covered: the amount derived from ``distance x company rate`` through
``quantity`` and ``total_amount`` (core then derives ``price_unit`` for a
no-cost category), the absence of VAT on a mileage expense and the guard
that rejects taxes on a mileage expense.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMileage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.employee = cls.env["hr.employee"].create({
            "name": "Mileage Employee",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Mileage Category (test)",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })

    def _open_form(self):
        form = Form(self.env["hr.expense"])
        form.name = "Mileage trip"
        form.employee_id = self.employee
        form.product_id = self.product
        form.payment_mode = "own_account"
        return form

    # ------------------------------------------------------------------
    # Amount computation
    # ------------------------------------------------------------------
    def test_amount_from_distance(self):
        with self._open_form() as form:
            form.od19_is_mileage = True
            form.od19_mileage_distance_km = 20.0
            expense = form.save()
        self.assertTrue(expense.od19_is_mileage)
        self.assertEqual(expense.od19_mileage_rate, 5.0)
        self.assertEqual(expense.quantity, 20.0)
        self.assertEqual(expense.total_amount, 100.0)
        self.assertEqual(expense.price_unit, 5.0)

    def test_distance_update_recomputes_amount(self):
        with self._open_form() as form:
            form.od19_is_mileage = True
            form.od19_mileage_distance_km = 30.0
            expense = form.save()
        self.assertEqual(expense.total_amount, 150.0)
        self.assertEqual(expense.price_unit, 5.0)

    # ------------------------------------------------------------------
    # No VAT on mileage
    # ------------------------------------------------------------------
    def test_tax_ids_empty_for_mileage(self):
        with self._open_form() as form:
            form.od19_is_mileage = True
            form.od19_mileage_distance_km = 10.0
            expense = form.save()
        self.assertFalse(expense.tax_ids)

    def test_taxes_rejected_on_mileage(self):
        tax = self.env["account.tax"].create({
            "name": "VAT 7% (test)",
            "amount": 7.0,
            "type_tax_use": "purchase",
        })
        with self._open_form() as form:
            form.od19_is_mileage = True
            form.od19_mileage_distance_km = 10.0
            expense = form.save()
        with self.assertRaises(ValidationError):
            expense.write({"tax_ids": [(6, 0, [tax.id])]})
