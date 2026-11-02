# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the Stamp Duty (อากรแสตมป์) register and rate table.

Covered: the seeded rate table (scale and fixed rates plus the 10,000 baht
cap), the automatic duty computation with the "round up to the next whole
unit" rule, the sequence naming, the state transitions, the report action
binding, the register content and the printable form.
"""

import math

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

RATE_MODEL = "od19.stamp.duty.rate"
DUTY_MODEL = "od19.stamp.duty"
REPORT_XMLID = "od19_thai_tax_reports.action_stamp_duty_register"
REPORT_NAME = "od19_thai_tax_reports.stamp_duty_register"
REPORT_MODEL = "report.od19_thai_tax_reports.stamp_duty_register"

RATE1_XMLID = "od19_thai_tax_reports.stamp_duty_rate_1"
RATE5_XMLID = "od19_thai_tax_reports.stamp_duty_rate_5"
RATE9_XMLID = "od19_thai_tax_reports.stamp_duty_rate_9"


@tagged("post_install", "-at_install")
class TestStampDuty(TransactionCase):
    """Basic tests for the stamp duty register."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.rate_rent = cls.env.ref(RATE1_XMLID)
        cls.rate_loan = cls.env.ref(RATE5_XMLID)
        cls.rate_bill = cls.env.ref(RATE9_XMLID)
        cls.partner = cls.env["res.partner"].create(
            {"name": "Stamp Duty Test Partner", "company_type": "company"}
        )

    def _create_duty(self, rate, base_amount, instrument_date="2026-04-10"):
        return self.env[DUTY_MODEL].create(
            {
                "rate_id": rate.id,
                "base_amount": base_amount,
                "instrument_date": fields.Date.from_string(instrument_date),
                "partner_id": self.partner.id,
            }
        )

    def _get_values(self, **context):
        ctx = {
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "company_id": self.company.id,
        }
        ctx.update(context)
        return self.env[REPORT_MODEL].with_context(**ctx)._get_report_values([])

    # ------------------------------------------------------------------
    # Rate table
    # ------------------------------------------------------------------
    def test_rate_table_seeded(self):
        self.assertEqual(self.rate_rent.rate_type, "scale")
        self.assertEqual(self.rate_rent.rate_amount, 1.0)
        self.assertEqual(self.rate_rent.base_unit, 1000.0)

        self.assertEqual(self.rate_loan.base_unit, 2000.0)
        self.assertEqual(self.rate_loan.max_amount, 10000.0)

        self.assertEqual(self.rate_bill.rate_type, "fixed")
        self.assertEqual(self.rate_bill.rate_amount, 3.0)

    # ------------------------------------------------------------------
    # Duty computation
    # ------------------------------------------------------------------
    def test_duty_scale_rounds_up(self):
        # 5,500 บาท / 1,000 = 5.5 -> ปัดขึ้นเป็น 6 หน่วย x 1 บาท = 6 บาท
        duty = self._create_duty(self.rate_rent, 5500.0)
        self.assertAlmostEqual(duty.duty_amount, 6.0, 2)
        self.assertEqual(duty.duty_amount, math.ceil(5500.0 / 1000.0) * 1.0)

    def test_duty_scale_exact_multiple(self):
        duty = self._create_duty(self.rate_rent, 5000.0)
        self.assertAlmostEqual(duty.duty_amount, 5.0, 2)

    def test_duty_loan_capped(self):
        # 50,000,000 บาท / 2,000 = 25,000 บาท -> เพดาน 10,000 บาท
        duty = self._create_duty(self.rate_loan, 50000000.0)
        self.assertAlmostEqual(duty.duty_amount, 10000.0, 2)

    def test_duty_fixed_rate(self):
        duty = self._create_duty(self.rate_bill, 0.0)
        self.assertAlmostEqual(duty.duty_amount, 3.0, 2)

    def test_duty_recomputes_on_base_change(self):
        duty = self._create_duty(self.rate_rent, 1000.0)
        self.assertAlmostEqual(duty.duty_amount, 1.0, 2)
        duty.base_amount = 2001.0
        self.assertAlmostEqual(duty.duty_amount, 3.0, 2)

    # ------------------------------------------------------------------
    # Naming and state
    # ------------------------------------------------------------------
    def test_sequence_naming(self):
        duty = self._create_duty(self.rate_rent, 1000.0)
        self.assertNotEqual(duty.name, "/")
        self.assertTrue(duty.name.startswith("ST/"))

    def test_state_transitions(self):
        duty = self._create_duty(self.rate_rent, 1000.0)
        self.assertEqual(duty.state, "draft")
        duty.action_mark_paid()
        self.assertEqual(duty.state, "paid")
        duty.action_reset_draft()
        self.assertEqual(duty.state, "draft")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def test_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    def test_report_lists_and_totals(self):
        rent = self._create_duty(self.rate_rent, 5500.0)
        loan = self._create_duty(self.rate_loan, 20000.0, "2026-04-15")

        values = self._get_values()
        names = [line["name"] for line in values["lines"]]
        self.assertIn(rent.name, names)
        self.assertIn(loan.name, names)
        # อากรเช่า = 6 บาท, อากรกู้ = 10 บาท
        self.assertAlmostEqual(values["total_duty"], 16.0, 2)
        self.assertAlmostEqual(values["total_base"], 25500.0, 2)
        self.assertEqual(len(values["rate_summary"]), 2)

    def test_report_excludes_out_of_range(self):
        duty = self._create_duty(self.rate_rent, 1000.0, "2026-05-05")
        values = self._get_values()
        names = [line["name"] for line in values["lines"]]
        self.assertNotIn(duty.name, names)

    def test_report_renders(self):
        self._create_duty(self.rate_rent, 5500.0)
        report = self.env.ref(REPORT_XMLID)
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "stamp_duty",
                    "date_from": "2026-04-01",
                    "date_to": "2026-04-30",
                    "company_id": self.company.id,
                }
            )
        )
        html, _report_type = (
            self.env["ir.actions.report"]
            .with_context(
                date_from=wizard.date_from,
                date_to=wizard.date_to,
                company_id=wizard.company_id.id,
            )
            ._render_qweb_html(report, wizard.ids)
        )
        rendered = html.decode()
        self.assertIn("อากรแสตมป์", rendered)
        self.assertIn("5,500.00", rendered)
        self.assertIn("6.00", rendered)

    def test_wizard_prints(self):
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "stamp_duty",
                    "date_from": "2026-04-01",
                    "date_to": "2026-04-30",
                    "company_id": self.company.id,
                }
            )
        )
        action = wizard.action_print()
        self.assertEqual(action["report_name"], REPORT_NAME)
