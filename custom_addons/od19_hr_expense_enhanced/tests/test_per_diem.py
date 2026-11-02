# -*- coding: utf-8 -*-
"""Tests for the per-diem allowance policy - Section 42(3) Revenue Code
(เบี้ยเลี้ยง ม.42(3)).

Covered: the standard limit taken from the company policy (domestic /
overseas), the over-limit flag, and the requirement for a reason when the
claimed allowance is above the limit.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPerDiem(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_per_diem_rate_domestic = 300.0
        cls.company.od19_per_diem_rate_overseas = 2000.0
        cls.partner = cls.env["res.partner"].create({"name": "Per Diem Employee"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Per Diem Employee",
            "work_contact_id": cls.partner.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Per Diem Product",
            "type": "service",
        })

    def _create_per_diem(self, days=2.0, region="domestic", total=600.0,
                         reason=None):
        vals = {
            "name": "Per diem allowance",
            "product_id": self.product.id,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
            "tax_ids": [(5, 0, 0)],
            "od19_is_per_diem": True,
            "od19_per_diem_region": region,
            "od19_per_diem_days": days,
            "total_amount": total,
        }
        if reason:
            vals["od19_per_diem_reason"] = reason
        return self.env["hr.expense"].create(vals)

    # ------------------------------------------------------------------
    # Limit computation
    # ------------------------------------------------------------------
    def test_limit_uses_domestic_rate(self):
        expense = self._create_per_diem(days=2.0, total=600.0)
        self.assertEqual(expense.od19_per_diem_standard_rate, 300.0)
        self.assertEqual(expense.od19_per_diem_limit, 600.0)
        self.assertFalse(expense.od19_per_diem_over_limit)

    def test_limit_uses_overseas_rate(self):
        expense = self._create_per_diem(
            days=3.0, region="overseas", total=6000.0)
        self.assertEqual(expense.od19_per_diem_standard_rate, 2000.0)
        self.assertEqual(expense.od19_per_diem_limit, 6000.0)
        self.assertFalse(expense.od19_per_diem_over_limit)

    # ------------------------------------------------------------------
    # Over-limit validation
    # ------------------------------------------------------------------
    def test_over_limit_requires_reason(self):
        with self.assertRaises(ValidationError):
            self._create_per_diem(days=2.0, total=1000.0)

    def test_over_limit_with_reason_is_allowed(self):
        expense = self._create_per_diem(
            days=2.0, total=1000.0, reason="Extra night on site")
        self.assertTrue(expense.od19_per_diem_over_limit)
        self.assertEqual(expense.od19_per_diem_reason, "Extra night on site")

    # ------------------------------------------------------------------
    # Non per-diem expenses are unaffected
    # ------------------------------------------------------------------
    def test_non_per_diem_is_ignored(self):
        expense = self.env["hr.expense"].create({
            "name": "Normal expense",
            "product_id": self.product.id,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
            "tax_ids": [(5, 0, 0)],
            "total_amount": 5000.0,
        })
        self.assertFalse(expense.od19_is_per_diem)
        self.assertEqual(expense.od19_per_diem_limit, 0.0)
        self.assertFalse(expense.od19_per_diem_over_limit)
