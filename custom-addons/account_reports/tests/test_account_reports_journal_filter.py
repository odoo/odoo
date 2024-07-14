# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountReportsJournalFilter(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.vanilla_company1 = cls.env['res.company'].create({'name': "Vanilla1"})
        cls.vanilla_company2 = cls.env['res.company'].create({'name': "Vanilla2"})

        # Force the test user to only access the vanilla companies
        cls.env.user.write({
            'company_ids': [Command.set((cls.vanilla_company1 + cls.vanilla_company2).ids)],
            'company_id': cls.vanilla_company1.id,
        })

        cls.report = cls.env.ref('account_reports.balance_sheet')

    def _assert_filter_journal(self, options, display_name, expected_values_list):
        journal_options = options['journals']
        self.assertEqual(options['name_journal_group'], display_name)
        self.assertEqual(len(journal_options), len(expected_values_list))
        for journal_option, expected_values in zip(journal_options, expected_values_list):
            if isinstance(expected_values, dict):
                self.assertDictEqual(expected_values, {k: journal_option.get(k) for k in expected_values})
            elif len(expected_values) == 2:
                record, selected = expected_values
                self.assertDictEqual(
                    {
                        'id': journal_option.get('id'),
                        'model': journal_option.get('model'),
                        'selected': journal_option.get('selected'),
                    },
                    {
                        'id': record.id,
                        'model': record._name,
                        'selected': selected,
                    },
                )

    def _quick_create_journal(self, name, company, journal_type='sale'):
        return self.env['account.journal'].create({
            'name': name,
            'code': name,
            'type': journal_type,
            'company_id': company.id,
        })

    def _quick_create_journal_group(self, name, company, excluded_journals):
        return self.env['account.journal.group'].create({
            'name': name,
            'excluded_journal_ids': [Command.set(excluded_journals.ids)],
            'company_id': company.id,
        })

    def test_journal_filter_single_company(self):
        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company1)
        j4 = self._quick_create_journal("j4", self.vanilla_company1)
        j5 = self._quick_create_journal("j5", self.vanilla_company1)
        j6 = self._quick_create_journal("j6", self.vanilla_company1)
        j7 = self._quick_create_journal("j7", self.vanilla_company1)
        j8 = self._quick_create_journal("j8", self.vanilla_company1)

        options = self.report.get_options()
        self._assert_filter_journal(options, "All Journals", [
            (j1, False),
            (j2, False),
            (j3, False),
            (j4, False),
            (j5, False),
            (j6, False),
            (j7, False),
            (j8, False),
        ])

        # Select j1/j2/j3
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j2 + j3).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j2, j3", [
            (j1, True),
            (j2, True),
            (j3, True),
            (j4, False),
            (j5, False),
            (j6, False),
            (j7, False),
            (j8, False),
        ])

        # Select j4/j5/j6
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j4 + j5 + j6).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j2, j3, j4, j5 and one other", [
            (j1, True),
            (j2, True),
            (j3, True),
            (j4, True),
            (j5, True),
            (j6, True),
            (j7, False),
            (j8, False),
        ])

        # Select j7
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') == j7.id:
                option_journal['selected'] = True
                break

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j2, j3, j4, j5 and 2 others", [
            (j1, True),
            (j2, True),
            (j3, True),
            (j4, True),
            (j5, True),
            (j6, True),
            (j7, True),
            (j8, False),
        ])

        # Select j8
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') == j8.id:
                option_journal['selected'] = True
                break

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            (j1, False),
            (j2, False),
            (j3, False),
            (j4, False),
            (j5, False),
            (j6, False),
            (j7, False),
            (j8, False),
        ])

    def test_journal_filter_multi_company(self):
        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company2)
        j4 = self._quick_create_journal("j4", self.vanilla_company2)
        j5 = self._quick_create_journal("j5", self.vanilla_company1)
        j6 = self._quick_create_journal("j6", self.vanilla_company1)
        j7 = self._quick_create_journal("j7", self.vanilla_company2)
        j8 = self._quick_create_journal("j8", self.vanilla_company2)

        options = self.report.get_options()
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            (j5, False),
            (j6, False),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
            (j7, False),
            (j8, False),
        ])

        # Select j1/j3/j5/j7
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j3 + j5 + j7).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j5, j3, j7", [
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j5, True),
            (j6, False),
            {'id': 'divider'},
            (j3, True),
            (j4, False),
            (j7, True),
            (j8, False),
        ])

    def test_journal_filter_with_groups_single_company(self):
        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company1)
        j4 = self._quick_create_journal("j4", self.vanilla_company1)
        j5 = self._quick_create_journal("j5", self.vanilla_company1)
        j6 = self._quick_create_journal("j6", self.vanilla_company1)

        g1 = self._quick_create_journal_group("g1", self.vanilla_company1, j2 + j4)
        g2 = self._quick_create_journal_group("g2", self.vanilla_company1, j2 + j5)

        options = self.report.get_options()
        self._assert_filter_journal(options, "g1", [
            {'id': 'divider'},
            (g1, True),
            (g2, False),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j3, True),
            (j4, False),
            (j5, True),
            (j6, True),
        ])

        # Check g2.
        options['__journal_group_action'] = {'action': 'add', 'id': g2.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g2", [
            {'id': 'divider'},
            (g1, False),
            (g2, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j3, True),
            (j4, True),
            (j5, False),
            (j6, True),
        ])

        # Uncheck g2.
        options['__journal_group_action'] = {'action': 'remove', 'id': g2.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (g1, False),
            (g2, False),
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            (j3, False),
            (j4, False),
            (j5, False),
            (j6, False),
        ])

    def test_journal_filter_with_groups_multi_company(self):
        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company1)
        j4 = self._quick_create_journal("j4", self.vanilla_company1)
        j5 = self._quick_create_journal("j5", self.vanilla_company2)
        j6 = self._quick_create_journal("j6", self.vanilla_company2)

        g1 = self._quick_create_journal_group("g1", self.vanilla_company1, j2 + j3)
        g2 = self._quick_create_journal_group("g2", self.vanilla_company1, j2 + j4)
        g3 = self._quick_create_journal_group("g3", self.vanilla_company2, j6)

        options = self.report.get_options()
        self._assert_filter_journal(options, "g1, g3", [
            {'id': 'divider'},
            (g1, True),
            (g2, False),
            (g3, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j3, False),
            (j4, True),
            {'id': 'divider'},
            (j5, True),
            (j6, False),
        ])

        # Check g2.
        options['__journal_group_action'] = {'action': 'add', 'id': g2.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g2, g3", [
            {'id': 'divider'},
            (g1, False),
            (g2, True),
            (g3, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j3, True),
            (j4, False),
            {'id': 'divider'},
            (j5, True),
            (j6, False),
        ])

        # Uncheck g2.
        options['__journal_group_action'] = {'action': 'remove', 'id': g2.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g3, j1, j2, j3, j4", [
            {'id': 'divider'},
            (g1, False),
            (g2, False),
            (g3, True),
            {'id': 'divider'},
            (j1, True),
            (j2, True),
            (j3, True),
            (j4, True),
            {'id': 'divider'},
            (j5, True),
            (j6, False),
        ])

        # Uncheck g3.
        options['__journal_group_action'] = {'action': 'remove', 'id': g3.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (g1, False),
            (g2, False),
            (g3, False),
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            (j3, False),
            (j4, False),
            {'id': 'divider'},
            (j5, False),
            (j6, False),
        ])

    def test_journal_filter_with_single_group_multi_company(self):
        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company2)
        j4 = self._quick_create_journal("j4", self.vanilla_company2)

        g1 = self._quick_create_journal_group("g1", self.vanilla_company1, j2)

        options = self.report.get_options()
        self._assert_filter_journal(options, "g1, j3, j4", [
            {'id': 'divider'},
            (g1, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            {'id': 'divider'},
            (j3, True),
            (j4, True),
        ])

        # Remove g1.
        options['__journal_group_action'] = {'action': 'remove', 'id': g1.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (g1, False),
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
        ])

        # Check j3.
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') == j3.id:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j3", [
            {'id': 'divider'},
            (g1, False),
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            {'id': 'divider'},
            (j3, True),
            (j4, False),
        ])

        # Check g1.
        options['__journal_group_action'] = {'action': 'add', 'id': g1.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g1, j3", [
            {'id': 'divider'},
            (g1, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            {'id': 'divider'},
            (j3, True),
            (j4, False),
        ])

        # Uncheck j3.
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') == j3.id:
                option_journal['selected'] = False

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g1", [
            {'id': 'divider'},
            (g1, True),
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
        ])

        # Uncheck g1.
        options['__journal_group_action'] = {'action': 'remove', 'id': g1.id}
        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (g1, False),
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
        ])

        # Check j3.
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j2).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j2", [
            {'id': 'divider'},
            (g1, False),
            {'id': 'divider'},
            (j1, True),
            (j2, True),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
        ])

    def test_journal_filter_with_groups_cash_flow_statement(self):
        """
        Test the behaviour of the journal filter with groups in a report
        that does not allow all journals, cash flow statement is a perfect
        fit for this use case
        """
        bnk = self._quick_create_journal("BNK", self.vanilla_company1, 'bank')
        csh = self._quick_create_journal("CSH", self.vanilla_company1, 'cash')
        misc = self._quick_create_journal("MISC", self.vanilla_company1, 'general')
        exch = self._quick_create_journal("EXCH", self.vanilla_company1, 'general')
        ifrs = self._quick_create_journal("IFRS", self.vanilla_company1, 'general')
        caba = self._quick_create_journal("CABA", self.vanilla_company1, 'general')
        inv = self._quick_create_journal("INV", self.vanilla_company1, 'sale')  # Not accepeted by the report
        bill = self._quick_create_journal("BILL", self.vanilla_company1, 'purchase')  # Not accepted by the report

        g1 = self._quick_create_journal_group("g1", self.vanilla_company1, inv + bill)
        g2 = self._quick_create_journal_group("g2", self.vanilla_company1, misc + bill)

        report = self.env.ref('account_reports.cash_flow_report')
        options = report.get_options()
        self._assert_filter_journal(options, "g1", [
            {'id': 'divider'},
            (g1, True),
            (g2, False),  # g2 should be displayed because it has journals taht are allowed in the report
            {'id': 'divider'},
            (bnk, True),
            (caba, True),
            (csh, True),
            (exch, True),
            (ifrs, True),
            (misc, True),
        ])

        # Check g2, all journals from g2 that are allowed in report should be selected
        options['__journal_group_action'] = {'action': 'add', 'id': g2.id}
        options = report.get_options(previous_options=options)
        self._assert_filter_journal(options, "g2", [
            {'id': 'divider'},
            (g1, False),
            (g2, True),
            {'id': 'divider'},
            (bnk, True),
            (caba, True),
            (csh, True),
            (exch, True),
            (ifrs, True),
            (misc, False),
        ])

        # Uncheck g2.
        options['__journal_group_action'] = {'action': 'remove', 'id': g2.id}
        options = report.get_options(previous_options=options)
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (g1, False),
            (g2, False),
            {'id': 'divider'},
            (bnk, False),
            (caba, False),
            (csh, False),
            (exch, False),
            (ifrs, False),
            (misc, False),
        ])

    def test_journal_filter_branch_company(self):
        """
        The purpose of this test is to ensure that the journal filter is
        well managed with sub companies.
        Each journal should appear once, even when it is shared within
        a company and its children.
        Also, journal from parent company should be display in the filter
        if only the child company is selected
        """
        self.vanilla_company1.write({'child_ids': [Command.create({'name': 'Vanilla3'})]})
        vanilla_company3 = self.vanilla_company1.child_ids[0]
        self.env.user.write({
            'company_ids': [Command.set((self.vanilla_company1 + self.vanilla_company2 + vanilla_company3).ids)],
            'company_id': self.vanilla_company1.id,
        })

        j1 = self._quick_create_journal("j1", self.vanilla_company1)
        j2 = self._quick_create_journal("j2", self.vanilla_company1)
        j3 = self._quick_create_journal("j3", self.vanilla_company2)
        j4 = self._quick_create_journal("j4", self.vanilla_company2)
        j5 = self._quick_create_journal("j5", self.vanilla_company1)
        j6 = self._quick_create_journal("j6", self.vanilla_company1)
        j7 = self._quick_create_journal("j7", self.vanilla_company2)
        j8 = self._quick_create_journal("j8", self.vanilla_company2)
        j9 = self._quick_create_journal("j9", vanilla_company3)
        j10 = self._quick_create_journal("j10", vanilla_company3)

        # With all companies selected, all journals should be displayed
        options = self.report.get_options()
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            (j5, False),
            (j6, False),
            {'id': 'divider'},
            (j3, False),
            (j4, False),
            (j7, False),
            (j8, False),
            {'id': 'divider'},
            (j10, False),
            (j9, False),
        ])

        # Select j1/j3/j5/j7
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j3 + j5 + j7 + j9).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j5, j3, j7, j9", [
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j5, True),
            (j6, False),
            {'id': 'divider'},
            (j3, True),
            (j4, False),
            (j7, True),
            (j8, False),
            {'id': 'divider'},
            (j10, False),
            (j9, True),
        ])

        # Select only the child company
        self.env.user.write({
            'company_ids': [Command.set((vanilla_company3).ids)],
            'company_id': vanilla_company3.id,
        })

        # Parent company journals should be displayed too
        options = self.report.get_options()
        self._assert_filter_journal(options, "All Journals", [
            {'id': 'divider'},
            (j1, False),
            (j2, False),
            (j5, False),
            (j6, False),
            {'id': 'divider'},
            (j10, False),
            (j9, False),
        ])

        # Select j1/j5/j10
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j5 + j10).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j5, j10", [
            {'id': 'divider'},
            (j1, True),
            (j2, False),
            (j5, True),
            (j6, False),
            {'id': 'divider'},
            (j10, True),
            (j9, False),
        ])

        # Select only the parent company
        self.env.user.write({
            'company_ids': [Command.set((self.vanilla_company1).ids)],
            'company_id': self.vanilla_company1.id,
        })

        # Only parent company journals should be displayed
        options = self.report.get_options()
        self._assert_filter_journal(options, "All Journals", [
            (j1, False),
            (j2, False),
            (j5, False),
            (j6, False),
        ])

        # Select j1/j5
        for option_journal in options['journals']:
            if option_journal.get('model') == 'account.journal' and option_journal.get('id') in (j1 + j5).ids:
                option_journal['selected'] = True

        options = self.report.get_options(previous_options=options)
        self._assert_filter_journal(options, "j1, j5", [
            (j1, True),
            (j2, False),
            (j5, True),
            (j6, False),
        ])
