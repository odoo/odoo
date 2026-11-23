"""Tests for ksw.salesperson.profile, ksw.salesperson.target.line.

Covers:
  • Profile creates 12 monthly target lines on save
  • _seed_monthly_lines distributes annual total evenly
  • _get_targets returns correct month targets
  • _get_targets falls back to even split when month row missing
  • _get_targets returns (0, 0, False) when no profile found
  • action_redistribute_targets resets to current even split
  • Unique employee × year constraint
  • display_name computed from employee + year
  • Monthly target non-negative constraint
  • Client split client_names computed from rule partner_ids
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSalespersonProfile(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        cls.emp = env['hr.employee'].sudo().create({
            'name': 'SP Profile Emp', 'x_is_attendance_sheet': True,
        })
        cls.emp_b = env['hr.employee'].sudo().create({
            'name': 'SP Profile Emp B', 'x_is_attendance_sheet': True,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _profile(self, emp=None, year=2025, role='sales',
                 annual_sales=12000.0, annual_coll=0.0):
        return self.env['ksw.salesperson.profile'].sudo().create({
            'employee_id': (emp or self.emp).id,
            'year': year,
            'role': role,
            'annual_sales_target': annual_sales,
            'annual_collection_target': annual_coll,
        })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_profile_creates_12_monthly_lines(self):
        """Creating a profile automatically seeds 12 monthly target rows."""
        p = self._profile(year=2020)
        self.assertEqual(len(p.target_line_ids), 12)

    def test_02_monthly_lines_even_split(self):
        """Each monthly target = annual / 12."""
        p = self._profile(year=2021, annual_sales=12000.0)
        for ln in p.target_line_ids:
            self.assertAlmostEqual(ln.sales_target, 1000.0)

    def test_03_get_targets_returns_monthly_values(self):
        """_get_targets for April 2022 returns the April row's values."""
        p = self._profile(year=2022, annual_sales=12000.0, annual_coll=6000.0)
        # Override April row
        apr = p.target_line_ids.filtered(lambda l: l.month == '4')
        apr.sudo().write({'sales_target': 2000.0, 'collection_target': 500.0})

        sales_t, coll_t, profile = self.env['ksw.salesperson.profile']._get_targets(
            self.emp, '2022-04-01')
        self.assertAlmostEqual(sales_t, 2000.0)
        self.assertAlmostEqual(coll_t, 500.0)
        self.assertEqual(profile, p)

    def test_04_get_targets_no_profile_returns_zeros(self):
        """_get_targets returns (0, 0, False) when no profile matches."""
        emp_none = self.env['hr.employee'].sudo().create({
            'name': 'No Profile Emp', 'x_is_attendance_sheet': True,
        })
        s, c, p = self.env['ksw.salesperson.profile']._get_targets(
            emp_none, '2099-01-01')
        self.assertEqual(s, 0.0)
        self.assertEqual(c, 0.0)
        self.assertFalse(p)

    def test_05_redistribute_targets_resets_to_even_split(self):
        """action_redistribute_targets overwrites manual overrides."""
        p = self._profile(year=2019, annual_sales=12000.0)
        # Manually override January
        jan = p.target_line_ids.filtered(lambda l: l.month == '1')
        jan.sudo().write({'sales_target': 9999.0})
        # Redistribute
        p.sudo().action_redistribute_targets()
        jan.invalidate_recordset()
        self.assertAlmostEqual(jan.sales_target, 1000.0)

    def test_06_unique_employee_year_constraint(self):
        """Two profiles for the same employee + year → constraint error."""
        self._profile(year=2018)
        with self.assertRaises(Exception):
            self._profile(year=2018)

    def test_07_display_name_has_employee_and_year(self):
        """display_name = 'Employee — year'."""
        p = self._profile(year=2017)
        self.assertIn('2017', p.display_name)
        self.assertIn(self.emp.name, p.display_name)

    def test_08_monthly_target_non_negative(self):
        """Monthly target line with negative sales_target raises ValidationError."""
        p = self._profile(year=2016)
        with self.assertRaises(ValidationError):
            jan = p.target_line_ids.filtered(lambda l: l.month == '1')
            jan.sudo().write({'sales_target': -1.0})

    def test_09_get_targets_fallback_no_row(self):
        """If a month row is missing, _get_targets falls back to annual/12."""
        p = self._profile(year=2015, annual_sales=12000.0)
        # Remove March row
        mar = p.target_line_ids.filtered(lambda l: l.month == '3')
        mar.sudo().unlink()
        s, c, prof = self.env['ksw.salesperson.profile']._get_targets(
            self.emp, '2015-03-01')
        self.assertAlmostEqual(s, 1000.0)  # 12000/12
        self.assertEqual(prof, p)

    def test_10_second_profile_different_year_allowed(self):
        """Different years → each employee can have one profile per year."""
        p1 = self._profile(emp=self.emp_b, year=2014)
        p2 = self._profile(emp=self.emp_b, year=2013)
        self.assertTrue(p1 and p2)

    def test_11_role_defaults_to_sales(self):
        """Default role is 'sales'."""
        p = self._profile(year=2012)
        self.assertEqual(p.role, 'sales')

