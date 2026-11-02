# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the TAS 12 deferred tax worksheet.

Covered: classification of temporary differences (taxable / deductible), the
closing balances, the movement of the period measured against the previous
worksheet, and the automatic journal entry posted on ``Post Deferred Tax``.
"""

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOd19DeferredTax(TransactionCase):
    """Basic tests for the TAS 12 deferred tax worksheet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dta_account = cls.env["account.account"].create(
            {
                "code": "X994001",
                "name": "Deferred Tax Asset Test",
                "account_type": "asset_current",
            }
        )
        cls.dtl_account = cls.env["account.account"].create(
            {
                "code": "X994002",
                "name": "Deferred Tax Liability Test",
                "account_type": "liability_current",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "code": "X994003",
                "name": "Deferred Tax Expense Test",
                "account_type": "expense",
            }
        )
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.company.write(
            {
                "od19_deferred_tax_asset_account_id": cls.dta_account.id,
                "od19_deferred_tax_liability_account_id": cls.dtl_account.id,
                "od19_deferred_tax_expense_account_id": cls.expense_account.id,
                "od19_deferred_tax_journal_id": cls.journal.id,
                "od19_deferred_tax_rate": 20.0,
            }
        )

    def _create_worksheet(self, lines=None, **overrides):
        vals = {
            "company_id": self.company.id,
            "date_from": fields.Date.today().replace(month=1, day=1),
            "date_to": fields.Date.today(),
            "line_ids": [(0, 0, line) for line in (lines or [])],
        }
        vals.update(overrides)
        return self.env["od19.deferred.tax.worksheet"].create(vals)

    # ------------------------------------------------------------------
    # Naming and classification
    # ------------------------------------------------------------------
    def test_worksheet_naming(self):
        worksheet = self._create_worksheet()
        self.assertTrue(worksheet.name.startswith("DT/"))

    def test_difference_classification(self):
        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
                {"name": "Deductible", "carrying_amount": 500.0, "tax_base": 700.0},
                {"name": "No difference", "carrying_amount": 300.0, "tax_base": 300.0},
            ]
        )
        taxable, deductible, none = worksheet.line_ids
        self.assertEqual(taxable.difference_type, "taxable")
        self.assertAlmostEqual(taxable.deferred_tax_amount, 200.0 * 0.20)
        self.assertEqual(deductible.difference_type, "deductible")
        self.assertAlmostEqual(deductible.deferred_tax_amount, 200.0 * 0.20)
        self.assertEqual(none.difference_type, "none")
        self.assertAlmostEqual(none.deferred_tax_amount, 0.0)

    def test_totals_compute(self):
        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
                {"name": "Deductible", "carrying_amount": 500.0, "tax_base": 700.0},
            ]
        )
        self.assertAlmostEqual(worksheet.total_dtl, 40.0)
        self.assertAlmostEqual(worksheet.total_dta, 40.0)
        self.assertAlmostEqual(worksheet.net_deferred, 0.0)

    # ------------------------------------------------------------------
    # Posting the journal entry
    # ------------------------------------------------------------------
    def test_post_creates_journal_entry(self):
        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
            ]
        )
        worksheet.action_post_deferred_tax()
        self.assertEqual(worksheet.state, "posted")
        self.assertTrue(worksheet.journal_entry_id)
        move = worksheet.journal_entry_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.ref, worksheet.name)
        dtl_line = move.line_ids.filtered(
            lambda line: line.account_id == self.dtl_account
        )
        expense_line = move.line_ids.filtered(
            lambda line: line.account_id == self.expense_account
        )
        self.assertAlmostEqual(dtl_line.credit, 40.0)
        self.assertAlmostEqual(expense_line.debit, 40.0)

    def test_post_requires_accounts(self):
        self.company.od19_deferred_tax_asset_account_id = False
        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
            ]
        )
        with self.assertRaises(UserError):
            worksheet.action_post_deferred_tax()

    def test_post_requires_movement(self):
        worksheet = self._create_worksheet(
            lines=[
                {"name": "No difference", "carrying_amount": 300.0, "tax_base": 300.0},
            ]
        )
        with self.assertRaises(UserError):
            worksheet.action_post_deferred_tax()

    def test_post_twice_raises(self):
        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
            ]
        )
        worksheet.action_post_deferred_tax()
        with self.assertRaises(UserError):
            worksheet.action_post_deferred_tax()

    # ------------------------------------------------------------------
    # Movement against the previous worksheet
    # ------------------------------------------------------------------
    def test_movement_from_previous_worksheet(self):
        previous = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 800.0},
            ]
        )
        previous.action_post_deferred_tax()

        worksheet = self._create_worksheet(
            lines=[
                {"name": "Taxable", "carrying_amount": 1000.0, "tax_base": 700.0},
            ],
            previous_worksheet_id=previous.id,
        )
        self.assertAlmostEqual(worksheet.opening_dtl, 40.0)
        self.assertAlmostEqual(worksheet.total_dtl, 60.0)
        self.assertAlmostEqual(worksheet.movement_dtl, 20.0)
        self.assertAlmostEqual(worksheet.movement_expense, 20.0)

        worksheet.action_post_deferred_tax()
        dtl_line = worksheet.journal_entry_id.line_ids.filtered(
            lambda line: line.account_id == self.dtl_account
        )
        self.assertAlmostEqual(dtl_line.credit, 20.0)
