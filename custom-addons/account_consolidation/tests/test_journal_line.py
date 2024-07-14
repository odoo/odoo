# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase
from odoo.exceptions import UserError
from unittest.mock import Mock
from odoo.models import ValidationError


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
