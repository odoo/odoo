# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch, Mock


@tagged('post_install', '-at_install')
class TestAccountConsolidationJournal(AccountConsolidationTestCase):
    # TESTS

    def test_balance(self):
        JournalLine = self.env['consolidation.journal.line']
        journal = self.env['consolidation.journal'].create({
            'name': "blah",
            'chart_id': self.chart.id,
        })
        amount = 100.0
        initial_count = JournalLine.search_count([])
        count = 100
        JournalLine.create([{
            'account_id': self._create_consolidation_account().id,
            'journal_id': journal.id,
            'amount': amount
        } for i in range(count)])
        # Will not be considered
        JournalLine.create({
            'account_id': self._create_consolidation_account().id,
            'journal_id': self.env['consolidation.journal'].create({
                'name': "bluh",
                'chart_id': self.chart.id,
            }).id,
            'amount': 6942
        })

        self.assertEqual(JournalLine.search_count([]), initial_count + count + 1)
        self.assertEqual(JournalLine.search_count([('journal_id', '=', journal.id)]), count)
        self.assertAlmostEqual(journal.balance, amount * count)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriodComposition._get_journal_lines_values')
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._get_journal_lines_values')
    def test_action_generate_journal_lines_when_origin_is_company_period(self, patched_company_period_method,
                                                                         patched_conso_method):
        Journal = self.env['consolidation.journal']
        accounts = [
            self._create_consolidation_account('First', 'end'),
            self._create_consolidation_account('Second', 'avg')
        ]
        expected = []
        for account in accounts:
            expected.append({'account_id': account.id, 'amount': 42 * (account.id + 1)})
        patched_company_period_method.return_value = expected

        ap = self._create_analysis_period()
        cps = (self._create_company_period(ap, self.default_company),
               self._create_company_period(ap, self.us_company))

        journals = []
        for i, cp in enumerate(cps):
            journals.append(Journal.create({
                'name': cp.mapped('company_id.name')[0],
                'company_period_id': cp.id,
                'period_id': ap.id,
                'chart_id': self.chart.id,
                'line_ids': [(0, 0, {'account_id': accounts[0].id, 'amount': (i + 1) * 4242})]
            }))

        journals[0].action_generate_journal_lines()
        patched_company_period_method.assert_called_once()
        patched_conso_method.assert_not_called()

        self.assertEqual(journals[1].line_ids.amount, 8484)
        self.assertEqual(len(journals[0].line_ids), 2)
        self.assertRecordValues(journals[0].line_ids, expected)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriodComposition._get_journal_lines_values')
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._get_journal_lines_values')
    def test_action_generate_journal_lines_when_origin_is_composition(self, patched_company_period_method,
                                                                      patched_conso_method):

        cap = self._create_analysis_period()
        uap = self._create_analysis_period()
        compo = self.env['consolidation.period.composition'].create({
            'composed_period_id': cap.id,
            'using_period_id': uap.id
        })
        journal = self.env['consolidation.journal'].create({
            'name': 'blah',
            'composition_id': compo.id,
            'chart_id': self.chart.id,
        })
        journal.action_generate_journal_lines()
        patched_company_period_method.assert_not_called()
        patched_conso_method.assert_called_once()

    def test__check_unique_origin(self):
        cap = self._create_analysis_period()
        uap = self._create_analysis_period()
        cp = self._create_company_period()
        compo = self.env['consolidation.period.composition'].create({
            'composed_period_id': cap.id,
            'using_period_id': uap.id
        })
        with self.assertRaises(ValidationError):
            self.env['consolidation.journal'].create({
                'name': 'blah',
                'composition_id': compo.id,
                'company_period_id': cp.id,
                'chart_id': self.chart.id,
            })

        journal = self.env['consolidation.journal'].create({
            'name': 'blah',
            'composition_id': compo.id,
            'chart_id': self.chart.id,
        })

        with self.assertRaises(ValidationError):
            journal.write({'company_period_id': cp.id})

        journal.write({'composition_id': False})
        journal.write({'company_period_id': cp.id})

        with self.assertRaises(ValidationError):
            journal.write({'composition_id': compo.id})


@tagged('post_install', '-at_install')
class TestAccountConsolidationJournalLine(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        self.dummy_account = self.env['consolidation.account'].create({'name': 'DUMMY'})

    # TESTS
    def test__check_conditional_unicity(self):
        account = self._create_consolidation_account()
        account2 = self._create_consolidation_account()
        editable_journal = self.env['consolidation.journal'].create({'name': 'BLAH', 'chart_id': self.chart.id})
        not_editable_journal = self.env['consolidation.journal'].create({
            'name': 'BLAH',
            'auto_generated': True,
            'chart_id': self.chart.id
        })

        self.env['consolidation.journal.line'].create({
            'journal_id': editable_journal.id,
            'account_id': account.id,
            'amount': 42,
        })
        # Can create multiple lines in an editable journal with the same account
        self.env['consolidation.journal.line'].create({
            'journal_id': editable_journal.id,
            'account_id': account.id,
            'amount': 42,
        })
        editable_journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': editable_journal.id,
            'account_id': account2.id,
            'amount': 42,
        })
        # Can update a journal line to set same account and not editable journal
        editable_journal_line.write({'account_id': account.id})

        self.env['consolidation.journal.line'].create({
            'journal_id': not_editable_journal.id,
            'account_id': account.id,
            'amount': 42,
        })

        # Cannot create a journal line for same account and not editable journal
        with self.assertRaises(ValidationError):
            self.env['consolidation.journal.line'].create({
                'journal_id': not_editable_journal.id,
                'account_id': account.id,
                'amount': 84,
            })

        not_editable_journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': not_editable_journal.id,
            'account_id': account2.id,
            'amount': 126
        })

        # Cannot update a journal line to set same account and not editable journal
        with self.assertRaises(UserError):
            not_editable_journal_line.write({'account_id': account.id})

    def test_grid_update_cell_editable_journal(self):
        journal = self.env['consolidation.journal'].create({'name': 'blah', 'chart_id': self.chart.id})
        account = self._create_consolidation_account()
        initial_amount = 42.0
        change_amount = 14.0
        journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': journal.id,
            'account_id': account.id,
            'amount': initial_amount
        })
        params = {
            'row_domain': [('id', '=', journal_line.id)],
            'cell_field': 'amount',
            'change': change_amount
        }
        journal_line \
            .with_context(default_account_id=journal_line.account_id.id, default_journal_id=journal.id) \
            .grid_update_cell(*params.values())
        created_lines = self.env['consolidation.journal.line'].search([
            ("id", "!=", journal_line.id),
            ("account_id", "=", journal_line.account_id.id),
            ("journal_id", "=", journal_line.journal_id.id),
        ])
        self.assertAlmostEqual(journal_line.amount, initial_amount)
        self.assertAlmostEqual(journal.balance, initial_amount + change_amount)
        self.assertEqual(len(created_lines), 1)

        self.assertAlmostEqual(created_lines.amount, change_amount)
        self.assertEqual(created_lines.note, 'Trial balance adjustment')
        self.assertEqual(created_lines.account_id.id, account.id)
        self.assertEqual(created_lines.journal_id.id, journal.id)

    def test_grid_update_cell(self):
        journal_line = self._create_journal_line(True)
        JournalLine = self.env['consolidation.journal.line']
        params = {
            'domain': [('id', '=', journal_line.id)],
            'cell_field': 'amount',
            'change': 14.0
        }
        journal_line = journal_line.with_context(
            default_account_id=journal_line.account_id.id,
            default_journal_id=journal_line.journal_id.id,
        )

        # JUST EDITED (no journal line created)
        # GIVEN
        # WHEN
        journal_line.grid_update_cell(*params.values())
        created_journal_line = JournalLine.search([
            ('id', '!=', journal_line.id),
            ('account_id', '=', journal_line.account_id.id),
            ('journal_id', '=', journal_line.journal_id.id),
        ])
        # THEN
        self.assertEqual(len(created_journal_line), 1, 'A journal line has been created')
        self.assertAlmostEqual(created_journal_line.amount, params['change'],
                               msg='Newly create journal line has the change amount as amount')

        # CANNOT EDIT AS LINKED TO COMPANY
        # GIVEN
        self._make_journal_line_not_editable(journal_line)
        amount_before = journal_line.amount
        # WHEN
        with self.assertRaises(UserError):
            journal_line.grid_update_cell(*params.values())
        # THEN
        self.assertAlmostEqual(journal_line.amount, amount_before, msg='Old journal line did not change')

        # CANNOT CREATE AS JOURNAL LINKED TO COMPANY (no journal line created)
        # GIVEN
        journal = self.env['consolidation.journal'].create({'name': 'bluh', 'auto_generated': True, 'chart_id': self.chart.id})

        # THEN
        with self.assertRaises(UserError):
            journal_line.with_context(default_journal_id=journal.id).grid_update_cell(*params.values())

        # CAN CREATE AS JOURNAL NOT AUTO-GENERATED
        # GIVEN
        journal.write({'auto_generated': False})
        params['change'] = 999.42
        amount_before = journal_line.amount
        # WHEN
        journal_line.with_context(default_journal_id=journal.id).grid_update_cell(*params.values())
        created_journal_line = JournalLine.search([
            ('id', 'not in', [journal_line.id, created_journal_line.id]),
            ('account_id', '=', journal_line.account_id.id),
            ('journal_id', '=', journal.id),
        ])
        # THEN
        self.assertAlmostEqual(journal_line.amount, amount_before, msg='Old journal line did not change')
        self.assertEqual(len(created_journal_line), 1, 'A journal line has been created')
        self.assertAlmostEqual(created_journal_line.amount, params['change'],
                               msg='Newly create journal line has the change amount as amount')

    def test_write(self):
        account = self._create_consolidation_account()
        journal = self.env['consolidation.journal'].create({'name': 'BLAH', 'auto_generated': True, 'chart_id': self.chart.id})
        journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': journal.id,
            'account_id': account.id,
            'amount': 42
        })
        with self.assertRaises(UserError):
            journal_line.write({'amount': 84})
        journal.write({'auto_generated': False})
        journal_line.write({'amount': 84})

    def test_unlink(self):
        account = self._create_consolidation_account()
        journal = self.env['consolidation.journal'].create({'name': 'BLAH', 'auto_generated': True, 'chart_id': self.chart.id})
        journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': journal.id,
            'account_id': account.id,
            'amount': 42
        })
        with self.assertRaises(UserError):
            journal_line.unlink()
        journal.write({'auto_generated': False})
        journal_line.unlink()

    def test__journal_is_editable(self):
        journal = self.env['consolidation.journal'].create({'name': 'blah', 'chart_id': self.chart.id})
        journal_line = self.env['consolidation.journal.line'].create({
            'journal_id': journal.id,
            'account_id': self.dummy_account.id
        })
        params = {
            'domain': [('id', '=', journal_line.id)],
            'column_field': 'journal_id',
            'column_value': journal.id
        }
        # Should be True as journal created
        self.assertTrue(journal_line._journal_is_editable(*params.values()))

        # Should be False as journal is linked to a company
        journal.auto_generated = True
        self.assertFalse(journal_line._journal_is_editable(*params.values()))

    # PRIVATES

    def _create_journal_line(self, editable=True):
        journal = self.env['consolidation.journal'].create({'name': 'blah', 'chart_id': self.chart.id})
        record = self.env['consolidation.journal.line'].create({
            'journal_id': journal.id,
            'account_id': self.dummy_account.id
        })
        if not editable:
            self._make_journal_line_not_editable(record)
        return record

    def _make_journal_line_not_editable(self, journal_line):
        journal_line.journal_id.write({'auto_generated': True})
