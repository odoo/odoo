"""Tests for ksw.commission.category — formula eval, validation, system-lock.

Covers:
  • Unique code constraint
  • _eval_formula: linear, conditional, non-QB fallback to 0.0
  • Invalid formula rejected at save time
  • Non-numeric formula result rejected
  • Quantity bounds validation (min/max, non-negative)
  • System category blocked from unlink; non-system can be deleted
  • Archiving a category (active=False)
"""
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestCommissionCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Pull two seeded categories for system-lock tests.
        cats = cls.env['ksw.commission.category'].search([
            ('code', 'in', ['location', 'other']),
        ])
        cls.cat_location = cats.filtered(lambda c: c.code == 'location')
        cls.cat_other = cats.filtered(lambda c: c.code == 'other')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_cat(self, **kw):
        defaults = {
            'name': 'Test Cat',
            'code': 'test_cat_unique_xyz',
            'kind': 'allowance',
        }
        defaults.update(kw)
        return self.env['ksw.commission.category'].sudo().create(defaults)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_unique_code_constraint(self):
        """Two categories with the same code → DB UNIQUE violation."""
        self._new_cat(code='dup_code_cat')
        with self.assertRaises(Exception):
            self._new_cat(code='dup_code_cat')

    def test_02_eval_formula_linear(self):
        """result = quantity * 100  →  _eval_formula(5) = 500."""
        cat = self._new_cat(
            code='qb_linear_test',
            is_quantity_based=True,
            formula='result = quantity * 100',
        )
        self.assertAlmostEqual(cat._eval_formula(5.0), 500.0)

    def test_03_eval_formula_conditional(self):
        """result = qty * 50 + (100 if qty >= 5 else 0)."""
        cat = self._new_cat(
            code='qb_cond_test',
            is_quantity_based=True,
            formula='result = qty * 50 + (100 if qty >= 5 else 0)',
        )
        self.assertAlmostEqual(cat._eval_formula(4.0), 200.0)   # no bonus
        self.assertAlmostEqual(cat._eval_formula(5.0), 350.0)   # with bonus

    def test_04_eval_formula_fallback_when_not_quantity_based(self):
        """Non-QB category → _eval_formula always returns 0.0."""
        cat = self._new_cat(code='non_qb_test', is_quantity_based=False)
        self.assertEqual(cat._eval_formula(999.0), 0.0)

    def test_05_invalid_formula_rejected(self):
        """Saving QB category with a syntax-error formula raises
        ValidationError at constrains time."""
        with self.assertRaises(ValidationError):
            self._new_cat(
                code='bad_formula_test',
                is_quantity_based=True,
                formula='result = quantity * *',  # SyntaxError
            )

    def test_06_formula_must_assign_result(self):
        """Formula that never assigns ``result`` produces 0.0 (falsy)
        — but does not crash; the constrains check verifies it is numeric."""
        # A formula that assigns result to a string should be rejected.
        with self.assertRaises(ValidationError):
            self._new_cat(
                code='str_result_test',
                is_quantity_based=True,
                formula='result = "not a number"',
            )

    def test_07_quantity_based_requires_formula(self):
        """QB category with no formula is rejected."""
        with self.assertRaises(ValidationError):
            self._new_cat(
                code='qb_no_formula',
                is_quantity_based=True,
                formula='',  # blank
            )

    def test_08_min_max_bounds_valid(self):
        """min_quantity < max_quantity → accepted."""
        cat = self._new_cat(
            code='bounds_ok_test',
            is_quantity_based=True,
            formula='result = quantity * 10',
            min_quantity=1.0,
            max_quantity=10.0,
        )
        self.assertEqual(cat.min_quantity, 1.0)

    def test_09_max_less_than_min_rejected(self):
        """max_quantity < min_quantity → ValidationError."""
        with self.assertRaises(ValidationError):
            self._new_cat(
                code='inv_bounds_test',
                is_quantity_based=True,
                formula='result = quantity * 10',
                min_quantity=5.0,
                max_quantity=2.0,
            )

    def test_10_negative_min_quantity_rejected(self):
        """min_quantity < 0 → ValidationError."""
        with self.assertRaises(ValidationError):
            self._new_cat(
                code='neg_min_test',
                is_quantity_based=True,
                formula='result = quantity * 10',
                min_quantity=-1.0,
            )

    def test_11_system_category_unlink_blocked(self):
        """Seeded system categories cannot be deleted (non-sudo)."""
        sys_cat = self.env['ksw.commission.category'].sudo().search([
            ('is_system', '=', True),
        ], limit=1)
        if not sys_cat:
            self.skipTest('No system category found — check seeding.')
        with self.assertRaises(UserError):
            sys_cat.unlink()

    def test_12_non_system_category_can_be_deleted(self):
        """User-created (non-system) categories can be unlinked."""
        cat = self._new_cat(code='deletable_cat_test')
        cat_id = cat.id
        cat.sudo().unlink()
        self.assertFalse(
            self.env['ksw.commission.category'].sudo().browse(cat_id).exists()
        )

    def test_13_archive_category(self):
        """Setting active=False archives the category."""
        cat = self._new_cat(code='archive_cat_test')
        cat.sudo().write({'active': False})
        self.assertFalse(cat.active)

    def test_14_eval_formula_zero_quantity(self):
        """_eval_formula(0) returns 0.0 for a linear formula."""
        cat = self._new_cat(
            code='qb_zero_test',
            is_quantity_based=True,
            formula='result = quantity * 50',
        )
        self.assertAlmostEqual(cat._eval_formula(0.0), 0.0)

