"""Tests for ksw.location.allowance.sheet and ksw.location.allowance.line.

Covers:
  • Sheet creation with sequence assignment
  • Period normalised to first-of-month
  • _compute_amounts: correct meal × price totals and grand total
  • Negative meal quantities rejected
  • Unique employee per sheet (DB constraint)
  • Confirm: sheet locked, commission sheet synced
  • Reset: commission amount cleared on commission sheet
  • Confirm auto-creates a commission sheet if none exists for the employee
  • Unique sheet per period (DB constraint)
  • total_allowance is sum of line totals
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLocationAllowance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        cls.emp1 = env['hr.employee'].sudo().create({
            'name': 'LA Emp1', 'x_is_attendance_sheet': True,
        })
        cls.emp2 = env['hr.employee'].sudo().create({
            'name': 'LA Emp2', 'x_is_attendance_sheet': True,
        })

        cls.period = '2026-04-01'

        # Set known meal prices via ir.config_parameter
        ICP = env['ir.config_parameter'].sudo()
        ICP.set_param('KSW_commissions.meal_breakfast_price', '10.0')
        ICP.set_param('KSW_commissions.meal_lunch_price', '20.0')
        ICP.set_param('KSW_commissions.meal_dinner_price', '15.0')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_la_sheet(self, period=None):
        return self.env['ksw.location.allowance.sheet'].sudo().create({
            'period': period or self.period,
        })

    def _add_la_line(self, sheet, emp, breakfast=0, lunch=0, dinner=0):
        return self.env['ksw.location.allowance.line'].sudo().create({
            'sheet_id': sheet.id,
            'employee_id': emp.id,
            'breakfast_qty': breakfast,
            'lunch_qty': lunch,
            'dinner_qty': dinner,
        })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_sequence_on_create(self):
        """Sheet gets a sequence-based name (not 'New')."""
        sheet = self._new_la_sheet()
        self.assertNotEqual(sheet.name, 'New')

    def test_02_period_normalised_to_first_of_month(self):
        """Period is normalised to the 1st of the given month."""
        sheet = self.env['ksw.location.allowance.sheet'].sudo().create({
            'period': '2026-05-17',
        })
        self.assertEqual(sheet.period.day, 1)
        self.assertEqual(sheet.period.month, 5)

    def test_03_compute_amounts_correct(self):
        """Line totals = qty × price for each meal type."""
        sheet = self._new_la_sheet(period='2026-03-01')
        line = self._add_la_line(sheet, self.emp1, breakfast=3, lunch=2, dinner=1)
        # Breakfast: 3×10 = 30; Lunch: 2×20 = 40; Dinner: 1×15 = 15
        self.assertAlmostEqual(line.breakfast_amount, 30.0)
        self.assertAlmostEqual(line.lunch_amount, 40.0)
        self.assertAlmostEqual(line.dinner_amount, 15.0)
        self.assertAlmostEqual(line.total_allowance, 85.0)

    def test_04_sheet_total_is_sum_of_lines(self):
        """Sheet.total_allowance = sum of all line totals."""
        sheet = self._new_la_sheet(period='2025-12-01')
        self._add_la_line(sheet, self.emp1, breakfast=2)   # 20
        self._add_la_line(sheet, self.emp2, lunch=3)        # 60
        self.assertAlmostEqual(sheet.total_allowance, 80.0)

    def test_05_negative_meal_qty_rejected(self):
        """Negative quantities raise ValidationError."""
        sheet = self._new_la_sheet(period='2025-11-01')
        with self.assertRaises(ValidationError):
            self._add_la_line(sheet, self.emp1, breakfast=-1)

    def test_06_unique_employee_per_sheet(self):
        """Same employee cannot appear twice on one sheet."""
        sheet = self._new_la_sheet(period='2025-10-01')
        self._add_la_line(sheet, self.emp1, breakfast=1)
        with self.assertRaises(Exception):
            self._add_la_line(sheet, self.emp1, lunch=1)

    def test_07_unique_sheet_per_period(self):
        """Only one location-allowance sheet per month."""
        self._new_la_sheet(period='2025-09-01')
        with self.assertRaises(Exception):
            self._new_la_sheet(period='2025-09-01')

    def test_08_confirm_sets_state_and_locks(self):
        """action_confirm transitions to confirmed and sets is_locked."""
        sheet = self._new_la_sheet(period='2025-08-01')
        self._add_la_line(sheet, self.emp1, breakfast=1)
        sheet.sudo().action_confirm()
        self.assertEqual(sheet.state, 'confirmed')
        self.assertTrue(sheet.is_locked)

    def test_09_confirm_syncs_location_allowance_to_commission_sheet(self):
        """After confirm, matching commission sheet reflects the allowance."""
        # Ensure the commission sheet exists first
        comm_sheet = self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': self.emp1.id,
            'period': '2025-07-01',
        })
        la_sheet = self._new_la_sheet(period='2025-07-01')
        self._add_la_line(la_sheet, self.emp1, lunch=4)  # 4 × 20 = 80
        la_sheet.sudo().action_confirm()

        comm_sheet.sudo()._compute_location_allowance()
        comm_sheet.sudo().flush_recordset(['location_allowance_amount'])
        self.assertAlmostEqual(comm_sheet.location_allowance_amount, 80.0)

    def test_10_reset_clears_location_allowance_on_commission_sheet(self):
        """Reset to draft clears location_allowance_amount on comm. sheet."""
        comm_sheet = self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': self.emp2.id,
            'period': '2025-06-01',
        })
        la_sheet = self._new_la_sheet(period='2025-06-01')
        self._add_la_line(la_sheet, self.emp2, dinner=2)  # 2 × 15 = 30
        la_sheet.sudo().action_confirm()

        comm_sheet.sudo()._compute_location_allowance()
        comm_sheet.sudo().flush_recordset(['location_allowance_amount'])
        self.assertAlmostEqual(comm_sheet.location_allowance_amount, 30.0)

        la_sheet.sudo().action_reset_to_draft()
        comm_sheet.sudo()._compute_location_allowance()
        comm_sheet.sudo().flush_recordset(['location_allowance_amount'])
        self.assertAlmostEqual(comm_sheet.location_allowance_amount, 0.0)

    def test_11_confirm_auto_creates_commission_sheet(self):
        """Confirm auto-creates a commission sheet for an employee that
        has no sheet for this period yet."""
        emp = self.env['hr.employee'].sudo().create({
            'name': 'LA AutoCreate Emp', 'x_is_attendance_sheet': True,
        })
        la_sheet = self._new_la_sheet(period='2025-05-01')
        self._add_la_line(la_sheet, emp, breakfast=5)
        la_sheet.sudo().action_confirm()

        comm_sheet = self.env['ksw.commission.sheet'].sudo().search([
            ('employee_id', '=', emp.id),
            ('period', '=', '2025-05-01'),
        ])
        self.assertTrue(comm_sheet,
                        'Commission sheet should be auto-created on confirm.')

    def test_12_zero_meals_allowance_is_zero(self):
        """Line with all zero quantities has total_allowance = 0."""
        sheet = self._new_la_sheet(period='2025-04-01')
        line = self._add_la_line(sheet, self.emp1, breakfast=0, lunch=0, dinner=0)
        self.assertAlmostEqual(line.total_allowance, 0.0)

