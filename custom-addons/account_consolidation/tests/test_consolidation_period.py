# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase

import json
from datetime import datetime, date
from unittest.mock import patch, ANY


@tagged('post_install', '-at_install')
class TestConsolidationPeriod(AccountConsolidationTestCase):
    # --- TESTS

    def test_unlink(self):
        AnalysisPeriod = self.env['consolidation.period']
        CompanyPeriod = self.env['consolidation.company_period']
        Composition = self.env['consolidation.period.composition']
        Journal = self.env['consolidation.journal']
        ap = self._create_analysis_period()
        ap2 = self._create_analysis_period()
        cp = self._generate_company_period(ap, 1, self.default_company)
        composition = Composition.create({
            'composed_period_id': ap.id,
            'using_period_id': ap2.id
        })
        journal = Journal.create({
            'name': 'BLAH',
            'period_id': ap.id,
            'chart_id': self.chart.id,
        })

        # CHECKING INITIAL CONDITIONS
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap.id)]), 1)
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap2.id)]), 1)
        self.assertEqual(CompanyPeriod.search_count([('id', '=', cp.id)]), 1)
        self.assertEqual(Composition.search_count([('id', '=', composition.id)]), 1)
        self.assertEqual(Journal.search_count([('id', '=', journal.id)]), 1)

        ap.unlink()

        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap.id)]), 0)
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap2.id)]), 1)
        self.assertEqual(CompanyPeriod.search_count([('id', '=', cp.id)]), 0)
        self.assertEqual(Composition.search_count([('id', '=', composition.id)]), 0)
        self.assertEqual(Journal.search_count([('id', '=', journal.id)]), 0)

        ap3 = self._create_analysis_period()
        composition2 = Composition.create({
            'composed_period_id': ap3.id,
            'using_period_id': ap2.id
        })

        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap3.id)]), 1)
        self.assertEqual(Composition.search_count([('id', '=', composition2.id)]), 1)

        ap2.unlink()

        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap2.id)]), 0)
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap3.id)]), 1)
        self.assertEqual(Composition.search_count([('id', '=', composition2.id)]), 0)

    # ----- ACTIONS

    def test_action_generate_journals(self):
        Journal = self.env['consolidation.journal']
        JournalLine = self.env['consolidation.journal.line']
        self._create_consolidation_account('First', 'end')
        self._create_consolidation_account('Second', 'avg')

        ap = self._create_analysis_period()
        self._generate_company_period(ap, 1, self.default_company)
        self._generate_company_period(ap, 2, self.us_company)

        # 1st state: from scratch
        ap.action_generate_journals()
        states = {'first': self._snapshot_state(ap.id)}

        # 2nd state : regenerates
        ap.action_generate_journals()

        # Same amount of journal & journal lines as before
        states['second'] = self._snapshot_state(ap.id)

        self.assertDictEqual(states['first']['amounts'], states['second']['amounts'],
                             "The same amount of journals and journal lines should be linked to analysis period")

        # old journals & journal lines have been deleted (and so new ones have been generated)
        self.assertEqual(0, Journal.search_count([('id', 'in', states['first']['ids']['journal'])]),
                         "Old journals have been deleted (and so new ones have been generated")
        self.assertEqual(0, JournalLine.search_count([('id', 'in', states['first']['ids']['journal_line'])]),
                         "Old journal lines have been deleted (and so new ones have been generated")

        # 3rd state : locked ap
        ap.action_close()
        ap.action_generate_journals()

        states['third'] = self._snapshot_state(ap.id)

        self.assertDictEqual(states['second'], states['third'],
                             'Nothing should have changed as analysis period is locked')

    # ----- PROTECTEDS

    # TEST _get_company_periods_default_values
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriod._get_previous_similiar_period',
        return_value=False)
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriod._get_company_periods_default_values_from_chart',
        return_value=[])
    def test__get_company_periods_default_values_to_chart(self, patched_get_company_values, patched_get_similar):
        ap = self._create_analysis_period()
        ap._get_company_periods_default_values()
        self.assertTrue(patched_get_similar.called)
        self.assertTrue(patched_get_company_values.called)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriod._get_previous_similiar_period')
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriod._get_company_periods_default_values_from_period',
        return_value=[])
    def test__get_company_periods_default_values_to_period(self, patched_get_company_values, patched_get_similar):
        ap = self._create_analysis_period()
        patched_get_similar.return_value = ap

        ap2 = self._create_analysis_period()
        ap2._get_company_periods_default_values()
        self.assertTrue(patched_get_similar.called)
        self.assertTrue(patched_get_company_values.called)
        patched_get_company_values.assert_called_with(ap)

    def test__get_previous_similiar_period(self):
        ap = self._create_analysis_period(chart=self.chart)
        ap2 = self._create_analysis_period(chart=self.chart)
        previous_similar = ap2._get_previous_similiar_period()
        self.assertNotEqual(previous_similar, False)
        self.assertEqual(previous_similar.id, ap.id)

    def test__get_company_periods_default_values_from_period(self):
        ap = self._create_analysis_period()
        cps = (self._generate_company_period(ap, 1, self.default_company),
               self._generate_company_period(ap, 2, self.us_company))

        ap2 = self._create_analysis_period()
        value_list = ap2._get_company_periods_default_values_from_period(ap)
        self.assertEqual(len(value_list), len(cps))
        fields = [
            'date_company_begin',
            'date_company_end',
            'currency_rate_avg',
            'currency_rate_end',
            'rate_control',
            'rate_ownership',
            'rate_consolidation',
            'consolidation_method'
        ]
        for i, cp in enumerate(cps):
            self.assertEqual(cp.company_id.id, value_list[i]['company_id'])
            for field in fields:
                self.assertEqual(getattr(cp, field), value_list[i][field])

    def test__get_company_periods_default_values_from_chart(self):
        ap = self._create_analysis_period(chart=self.chart)
        values_list = ap._get_company_periods_default_values_from_chart()
        self.assertEqual(len(values_list), len(self.chart.company_ids))
        for values in values_list:
            self.assertEqual(len(values), 10)
            self.assertIn('chart_id', values)
            self.assertIn('date_company_begin', values)
            self.assertIn('date_company_end', values)
            self.assertIn('company_id', values)
            self.assertIn('currency_rate_avg', values)
            self.assertIn('currency_rate_end', values)
            self.assertIn('rate_control', values)
            self.assertIn('rate_ownership', values)
            self.assertIn('rate_consolidation', values)
            self.assertIn('consolidation_method', values)

        for company_id in self.chart.company_ids.ids:
            index = -1
            for i, values in enumerate(values_list):
                if values['company_id'] == company_id:
                    index = i
            self.assertNotEqual(index, -1, 'Default values for company %s should be generated' % company_id)
            company_values = values_list[index]
            self.assertEqual(company_values['chart_id'].id, self.chart.id)
            self.assertEqual(company_values['date_company_begin'], ap.date_analysis_begin)
            self.assertEqual(company_values['date_company_end'], ap.date_analysis_end)

    def test__dashboard_sections(self):
        AccountSection = self.env['consolidation.group']
        ap = self._create_analysis_period()
        sections = (
            AccountSection.create({'name': 'Section 1', 'show_on_dashboard': True, 'chart_id': self.chart.id}),
            AccountSection.create({'name': 'Section 2', 'show_on_dashboard': True, 'chart_id': self.chart.id}),
            AccountSection.create(
                {'name': 'Section Hidden', 'show_on_dashboard': False, 'chart_id': self.chart.id})
        )

        i = 1
        step = 42
        for section in sections:
            accounts = (
                self.env['consolidation.account'].create({'name': 'BLAH #' + str(i), 'group_id': section.id}),
                self.env['consolidation.account'].create({'name': 'BLIH #' + str(i), 'group_id': section.id}))
            for account in accounts:
                journal = self.env['consolidation.journal'].create({
                    'name': 'BLAH',
                    'period_id': ap.id,
                    'chart_id': self.chart.id,
                })
                self.env['consolidation.journal.line'].create({
                    'account_id': account.id,
                    'journal_id': journal.id,
                    'amount': i * step
                })
                i += 1

        excl_section = AccountSection.create({'name': 'Not listed section', 'chart_id': self.chart.id})
        journal = self.env['consolidation.journal'].create({
            'name': 'BLAH',
            'period_id': self._create_analysis_period().id,
            'chart_id': self.chart.id,
        })
        self.env['consolidation.journal.line'].create({
            'account_id': self.env['consolidation.account'].create(
                {'name': 'Excluded account', 'group_id': excl_section.id}).id,
            'journal_id': journal.id
        })

        expected_amounts = [
            ap._format_value(step + 2 * step),  # i=1 & i=2 loop step
            ap._format_value(3 * step + 4 * step)  # i=3 & i=4 loop step
        ]
        dashboard_sections = json.loads(ap.dashboard_sections)
        self.assertListEqual([val.get('value') for val in dashboard_sections], expected_amounts)
        self.assertEqual(list(map(lambda x: x.name, sections[:2])), [val.get('name') for val in dashboard_sections])

    def test__journal_ids_count(self):
        Journal = self.env['consolidation.journal']
        ap = self._create_analysis_period()
        amount_of_journals = 42
        Journal.create([{'name': 'a', 'period_id': ap.id, 'chart_id': self.chart.id,}] * amount_of_journals)
        self.assertEqual(ap.journal_ids_count, amount_of_journals)

    def test__display_dates(self):
        ap_same_month_and_year = self._create_analysis_period(start_date='2019-01-01', end_date='2019-01-31')
        expected_str = ap_same_month_and_year.date_analysis_begin.strftime('%b %Y')  # Jan 2019
        self.assertEqual(ap_same_month_and_year.display_dates.lower(), expected_str.lower())

        ap_same_month = self._create_analysis_period(start_date='2019-01-01', end_date='2020-01-31')
        expected_str = '-'.join((ap_same_month.date_analysis_begin.strftime('%b %Y'),  # Jan 2019-Jan 2020
                                 ap_same_month.date_analysis_end.strftime('%b %Y')))
        self.assertEqual(ap_same_month.display_dates.lower(), expected_str.lower())

        ap_same_year = self._create_analysis_period(start_date='2019-01-01', end_date='2019-12-31')
        expected_str = '-'.join((ap_same_year.date_analysis_begin.strftime('%b'),  # Jan-Dec 2019
                                 ap_same_year.date_analysis_end.strftime('%b %Y')))
        self.assertEqual(ap_same_year.display_dates.lower(), expected_str.lower())

        ap_nothing_common = self._create_analysis_period(start_date='2019-01-01', end_date='2020-06-01')
        expected_str = '-'.join((ap_nothing_common.date_analysis_begin.strftime('%b %Y'),  # Jan 2019-Jun 2020
                                 ap_nothing_common.date_analysis_end.strftime('%b %Y')))
        self.assertEqual(ap_nothing_common.display_dates.lower(), expected_str.lower())

    # --- HELPERS

    def _generate_company_period(self, ap, nb, company):
        return self._create_company_period(period=ap, rate_consolidation=10 * nb, company=company)

    def _snapshot_state(self, ap_id):
        journals = self.env['consolidation.journal'].search([('period_id', '=', ap_id)])
        journal_lines = self.env['consolidation.journal.line'].search([('period_id', '=', ap_id)])
        return {
            'ids': {
                'journal': journals.ids,
                'journal_line': journal_lines.ids,
            },
            'amounts': {
                'journal': len(journals),
                'journal_line': len(journal_lines),
            }
        }


@tagged('post_install', '-at_install')
class TestConsolidationPeriodComposition(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        # Child conso's
        ap = self._create_analysis_period(chart=self.chart)

        usd_chart = self.env['consolidation.chart'].create({'name': 'USD chart', 'currency_id': self.env.ref('base.USD').id})
        usd_ap = self._create_analysis_period(chart=usd_chart)
        # Children accounts
        children_accounts = [
            self._create_consolidation_account('Child account 1', chart=self.chart, section=None),
            self._create_consolidation_account('Child account 2', chart=self.chart, section=None)
        ]
        usd_children_accounts = [
            self._create_consolidation_account('USD Child account 1', chart=usd_chart, section=None),
            self._create_consolidation_account('USD Child account 2', chart=usd_chart, section=None)
        ]
        # Account in child conso but not mapped to an account in super conso
        other_account = self._create_consolidation_account('Child account 2', chart=self.chart, section=None)

        # Parent/Super conso
        super_chart = self.env['consolidation.chart'].create({'name': 'Super chart', 'currency_id': self.env.ref('base.EUR').id})
        super_ap = self._create_analysis_period(chart=super_chart)

        # Super account (in super conso)
        self.super_account = self._create_consolidation_account('Super account', chart=super_chart, section=None)

        # Link account to children accounts
        self.super_account.write({'using_ids': [(6, 0, [ca.id for ca in children_accounts + usd_children_accounts])]})

        # Link periods
        Compo = self.env['consolidation.period.composition']
        compo = Compo.create({
            'composed_period_id': ap.id,
            'rate_consolidation': 50.0,
            'using_period_id': super_ap.id
        })
        usd_compo = Compo.create({
            'composed_period_id': usd_ap.id,
            'rate_consolidation': 20.0,
            'currency_rate': 0.25,
            'using_period_id': super_ap.id
        })

        # Create journal lines for each children accounts (and one for the other account but it won't affect the result)
        self.env['consolidation.journal'].create({
            'name': 'bluh',
            'period_id': ap.id,
            'auto_generated': True,
            'chart_id': self.chart.id,
            'line_ids': [
                (0, 0, {
                    'account_id': children_accounts[0].id,
                    'amount': 42
                }),
                (0, 0, {
                    'account_id': children_accounts[1].id,
                    'amount': 4200
                }),
                (0, 0, {
                    'account_id': other_account.id,
                    'amount': 420000
                })
            ]
        })
        self.env['consolidation.journal'].create({
            'name': 'USD bluh',
            'period_id': usd_ap.id,
            'auto_generated': True,
            'chart_id': usd_chart.id,
            'line_ids': [
                (0, 0, {
                    'account_id': usd_children_accounts[0].id,
                    'amount': 8000
                }),
                (0, 0, {
                    'account_id': usd_children_accounts[1].id,
                    'amount': 12000
                })
            ]
        })
        self.compo = Compo.browse(compo.id)
        self.usd_compo = Compo.browse(usd_compo.id)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriod.action_generate_journals',
        return_value=False)
    def test_generate_journal(self, patched_ap_action_generate_journals):
        AccountJournal = self.env['consolidation.journal']
        self.compo._generate_journal()
        # Checking that the journal generation of this composition triggers the generations of
        # the composed analysis period
        patched_ap_action_generate_journals.assert_called_once()
        last_journal = AccountJournal.search([], order='id desc', limit=1)

        self.assertEqual(last_journal.name, self.compo.composed_period_id.chart_name)
        self.assertTrue(last_journal.auto_generated)
        self.assertEqual(last_journal.composition_id, self.compo)
        self.assertEqual(last_journal.period_id, self.compo.using_period_id)
        self.assertEqual(len(last_journal.line_ids), 1)
        amount_of_journals = AccountJournal.search_count([])
        self.compo._generate_journal()
        self.assertEqual(amount_of_journals, AccountJournal.search_count([]), 'Old journal has been deleted')

    def test__get_journal_lines_values(self):
        jl_values = self.compo._get_journal_lines_values()
        self.assertEqual(len(jl_values), 1)
        jl_value = jl_values[0]
        self.assertEqual(jl_value['account_id'], self.super_account.id)
        self.assertEqual(jl_value['amount'], 2121.0)

    def test__get_total_amount(self):
        # should be (4200 + 42) * 0.5 = 2121.0
        self.assertAlmostEqual(self.compo._get_total_amount(self.super_account), 2121.0)
        # should be ((12000 + 8000) * 0.2) * 0.25 = 1000.0
        #       consolidation rate        currency_rate
        self.assertAlmostEqual(self.usd_compo._get_total_amount(self.super_account), 1000.0)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationPeriodComposition._get_default_currency_rate',
        return_value=2.0)
    def test__onchange_composed_chart_currency_id(self, mocked_method):
        self.compo._onchange_composed_chart_currency_id()
        self.usd_compo._onchange_composed_chart_currency_id()
        self.assertFalse(self.compo.currencies_are_different)
        self.assertTrue(self.usd_compo.currencies_are_different)
        self.assertAlmostEqual(self.compo.currency_rate, 1.0)
        self.assertAlmostEqual(self.usd_compo.currency_rate, mocked_method.return_value)

    @patch('odoo.addons.base.models.res_currency.Currency._get_conversion_rate', return_value=150.0)
    def test__get_default_currency_rate(self, mocked_method):
        rate = self.usd_compo._get_default_currency_rate()
        self.assertEqual(rate, mocked_method.return_value)
        mocked_method.assert_called_once_with(self.usd_compo.composed_chart_currency_id,
                                              self.usd_compo.using_chart_currency_id, self.env.company, ANY)


@tagged('post_install', '-at_install')
class TestConsolidationCompanyPeriod(AccountConsolidationTestCase):
    def test_get_display_name(self):
        ap = self._create_analysis_period(start_date='2019-01-01', end_date='2019-01-31')
        cp = self._create_company_period(period=ap, start_date='2019-01-01', end_date='2019-01-31')
        expected_str = cp.company_name
        self.assertEqual(expected_str, cp.display_name)

        # SAME MONTH & YEAR
        cp.write({
            'date_company_begin': datetime.strptime('2019-02-01', '%Y-%m-%d'),
            'date_company_end': datetime.strptime('2019-02-28', '%Y-%m-%d')
        })
        expected_str = cp.company_name + ' (' + cp.date_company_begin.strftime('%b %Y') + ')'
        self.assertEqual(expected_str, cp.display_name)

        # SAME MONTH BUT DIFFERENT YEAR
        cp.write({
            'date_company_begin': datetime.strptime('2019-01-01', '%Y-%m-%d'),
            'date_company_end': datetime.strptime('2020-01-31', '%Y-%m-%d')
        })
        expected_str = cp.company_name + ' (' + '-'.join((cp.date_company_begin.strftime('%b %Y'),  # Jan 2019-Jan 2020
                                                          cp.date_company_end.strftime('%b %Y'))) + ')'
        self.assertEqual(expected_str, cp.display_name)

        # SAME YEAR BUT DIFFERENT YEAR
        cp.write({
            'date_company_begin': datetime.strptime('2019-01-01', '%Y-%m-%d'),
            'date_company_end': datetime.strptime('2019-12-31', '%Y-%m-%d')
        })
        expected_str = cp.company_name + ' (' + '-'.join((cp.date_company_begin.strftime('%b'),  # # Jan-Dec 2019
                                                          cp.date_company_end.strftime('%b %Y'))) + ')'
        self.assertEqual(expected_str, cp.display_name)

        # DIFFERENT YEAR AND MONTH
        cp.write({
            'date_company_begin': datetime.strptime('2019-01-01', '%Y-%m-%d'),
            'date_company_end': datetime.strptime('2020-06-01', '%Y-%m-%d')
        })
        expected_str = cp.company_name + ' (' + '-'.join((cp.date_company_begin.strftime('%b %Y'),  # Jan 2019-Jun 2020
                                                          cp.date_company_end.strftime('%b %Y'))) + ')'
        self.assertEqual(expected_str, cp.display_name)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._get_total_balance_and_audit_lines',
        return_value=(42.0, []))
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._apply_rates',
        return_value=191289.0)
    def test_generate_journal(self, patch_apply_rates, patched_get_total_balance):
        Journal = self.env['consolidation.journal']
        JournalLine = self.env['consolidation.journal.line']
        self._create_consolidation_account('First', 'end')
        self._create_consolidation_account('Second', 'avg')

        ap = self._create_analysis_period()
        cp = self._create_company_period(period=ap, rate_consolidation=10, company=self.default_company)
        cp._generate_journal()
        journals = Journal.search([('company_period_id', '=', cp.id)])
        self.assertEqual(1, len(journals), "Company period should only have one Journal")
        journal = journals[0]
        self.assertEqual(journal.period_id.id, ap.id, "Created journal should have the right analysis period")

        journal_lines = JournalLine.search([('journal_id', '=', journal.id)])
        self.assertEqual(2, len(journal_lines), 'Generated journal should have two journal lines')
        self.assertNotEqual(journal_lines[0].account_id, journal_lines[1].account_id,
                            'Generated journals lines should be linked to different accounts')
        for journal_line in journal_lines:
            self.assertAlmostEqual(journal_line.currency_amount, patched_get_total_balance.return_value[0],
                                   msg='Generated journals should have the right currency amount')
            self.assertAlmostEqual(journal_line.amount, patch_apply_rates.return_value,
                                   msg='Generated journals should have the right amount')

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._get_total_balance_and_audit_lines',
        return_value=(420.0, []))
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._apply_rates',
        return_value=191289.0)
    def test_get_journal_lines_values(self, patch_apply_rates, patch_get_total_balance):
        accounts = (
            self._create_consolidation_account('First', 'end'),
            self._create_consolidation_account('Second', 'avg')
        )
        ap = self._create_analysis_period()
        cps = (self._create_company_period(period=ap, rate_consolidation=10.0, company=self.default_company),
               self._create_company_period(period=ap, rate_consolidation=20.0, company=self.us_company))
        expected = [{
            'account_id': accounts[0].id,
            'amount': patch_apply_rates.return_value,
            'currency_amount': patch_get_total_balance.return_value[0],
            'move_line_ids': [(6, 0, patch_get_total_balance.return_value[1])]
        }, {
            'account_id': accounts[1].id,
            'amount': patch_apply_rates.return_value,
            'currency_amount': patch_get_total_balance.return_value[0],
            'move_line_ids': [(6, 0, patch_get_total_balance.return_value[1])]}
        ]
        for cp in cps:
            result = cp._get_journal_lines_values()
            self.assertListEqual(expected, result)

    def test__apply_historical_rates(self):
        ap = self._create_analysis_period()
        consolidation_rate = 50
        cp = self._create_company_period(period=ap, rate_consolidation=consolidation_rate,
                                         company=self.us_company, start_date='2010-01-01', end_date='2024-12-31')
        account_credit = self._create_account('111', 'Credit account', company=self.us_company)
        consolidation_account = self._create_consolidation_account()
        consolidation_account.write({'account_ids': [(4, account_credit.id)]})
        move_date = '2014-01-31'
        self.env['res.currency.rate'].create({
            'name': move_date,
            'company_id': self.us_company.id,
            'currency_id': self.env.ref('base.EUR').id,
            'rate': 0.8
        })
        self.env['res.currency.rate'].create({
            'name': '2019-01-31',
            'company_id': self.us_company.id,
            'currency_id': self.env.ref('base.EUR').id,
            'rate': 350.27
        })
        move = self._create_basic_move(1000, company=self.us_company, move_date=move_date,
                                       account_credit=account_credit)
        move_line = move.line_ids[0]
        # = (50/100) * (mlb/1.25)
        # = 0.5 * 0.8 * mlb
        expected_amount = 0.4 * move_line.balance
        self.assertAlmostEqual(cp._apply_historical_rates(move_line), expected_amount)

    def test__apply_historical_rates_with_fixed_rates(self):
        ap = self._create_analysis_period()
        consolidation_rate = 50
        cp = self._create_company_period(period=ap, rate_consolidation=consolidation_rate,
                                         company=self.us_company, start_date='2010-01-01', end_date='2024-12-31')
        self.env['consolidation.rate'].create([
            {
                'date_start': '2014-01-01',
                'date_end': '2014-12-31',
                'rate': 1.5,
                'company_id': self.us_company.id,
                'chart_id': cp.chart_id.id
            },
            {
                'date_start': '2013-01-01',
                'date_end': '2013-12-31',
                'rate': 157.34,
                'company_id': self.us_company.id,
                'chart_id': cp.chart_id.id
            },
            {
                'date_start': '2013-01-01',
                'date_end': '2013-12-31',
                'rate': 0.001,
                'company_id': self.default_company.id,
                'chart_id': cp.chart_id.id
            }
        ])
        account_credit = self._create_account('111', 'Credit account', company=self.us_company)
        consolidation_account = self._create_consolidation_account()
        consolidation_account.write({'account_ids': [(4, account_credit.id)]})
        move_date = '2014-01-31'
        self.env['res.currency.rate'].create({
            'name': move_date,
            'company_id': self.us_company.id,
            'currency_id': self.us_company.currency_id.id,
            'rate': 1.25
        })
        self.env['res.currency.rate'].create({
            'name': '2019-01-31',
            'company_id': self.us_company.id,
            'currency_id': self.us_company.currency_id.id,
            'rate': 350.27
        })
        move = self._create_basic_move(1000, company=self.us_company, move_date=move_date,
                                       account_credit=account_credit)
        move_line = move.line_ids[0]
        # = (50/100) * (mlb*1.5) (1.5 = good rate above)
        # = 0.75 * mlb
        expected_amount = 0.75 * move_line.balance
        self.assertAlmostEqual(cp._apply_historical_rates(move_line), expected_amount)
        rate = self.env['consolidation.rate'].search([('rate', '=', 1.5)])
        rate.rate = 3.0
        # Check if the rate cache is properly invalidated
        self.assertAlmostEqual(cp._apply_historical_rates(move_line), 1.5*move_line.balance)

    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._convert')
    @patch(
        'odoo.addons.account_consolidation.models.consolidation_period.ConsolidationCompanyPeriod._apply_consolidation_rate')
    def test__apply_rates(self, patched_apply_consolidation_rate, patched_convert):
        cp = self._create_company_period(start_date='2019-01-01', end_date='2019-01-31', company=self.us_company)
        ca = self._create_consolidation_account()
        amount = 56554561
        patched_convert.return_value = 15000
        patched_apply_consolidation_rate.return_value = 13500
        self.assertAlmostEqual(patched_apply_consolidation_rate.return_value, cp._apply_rates(amount, ca))
        patched_convert.assert_called_once_with(amount, ca.currency_mode)
        patched_apply_consolidation_rate.assert_called_once_with(patched_convert.return_value)
        pass

    def test__get_total_balance_and_audit_lines(self):
        journals = {
            'good': self.env['account.journal'].create({'name': 'Bank 123456', 'code': 'BNK67', 'type': 'bank',
                                                        'bank_acc_number': '123456', 'company_id': self.default_company.id}),
            'ignored': self.env['account.journal'].create({'name': 'Outlier', 'code': 'OUT', 'type': 'bank',
                                                           'bank_acc_number': '12345226', 'company_id': self.default_company.id})
        }
        revenue_type = 'income'
        dummy_account = self._create_account('003', 'NOTCONSIDERATED', company=self.default_company, type=revenue_type)
        not_ignored_accounts = [
            self._create_account('001', 'RCV', company=self.default_company, type=revenue_type),
            self._create_account('002', 'RCV2', company=self.default_company, type=revenue_type),
        ]
        conso_account = self.env['consolidation.account'].create({
            'name': 'Test account',
            'account_ids': [(4, x.id) for x in not_ignored_accounts]
        })

        cp = self._create_company_period(company=self.default_company)
        cp.exclude_journal_ids = journals['ignored']

        # The first move line should be ignored (because not in one of the accounts of the consolidation account)
        not_ignored_amounts = [100, 1000]
        right_move = self.env['account.move'].create({
            'date': '2019-01-31',
            'journal_id': journals['good'].id,
            'line_ids': [
                (0, 0, {
                    'account_id': dummy_account.id,
                    'credit': sum(not_ignored_amounts)
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[0],
                    'debit': not_ignored_amounts[0]
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[1],
                    'debit': not_ignored_amounts[1]
                }),
            ]
        })
        right_move.action_post()

        # Ignored as not posted
        self.env['account.move'].create({
            'date': '2019-01-31',
            'journal_id': journals['good'].id,
            'line_ids': [
                (0, 0, {
                    'account_id': dummy_account.id,
                    'credit': sum(not_ignored_amounts)
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[0],
                    'debit': not_ignored_amounts[0]
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[1],
                    'debit': not_ignored_amounts[1]
                }),
            ]
        })

        # All should be ignored as not in the period
        self.env['account.move'].create({
            'date': '2017-01-31',
            'journal_id': journals['good'].id,
            'line_ids': [
                (0, 0, {
                    'account_id': dummy_account.id,
                    'credit': 1100
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[0],
                    'debit': 100
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[1],
                    'debit': 1000
                }),
            ]
        }).action_post()

        # All should be ignored as not in the right journal
        self.env['account.move'].create({
            'date': '2019-01-31',
            'journal_id': journals['ignored'].id,
            'line_ids': [
                (0, 0, {
                    'account_id': dummy_account.id,
                    'credit': 1100
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[0],
                    'debit': 100
                }),
                (0, 0, {
                    'account_id': conso_account.mapped('account_ids.id')[1],
                    'debit': 1000
                }),
            ]
        }).action_post()

        total_balance, associated_move_line_ids = cp._get_total_balance_and_audit_lines(conso_account)
        self.assertAlmostEqual(sum(not_ignored_amounts), total_balance)
        self.assertEqual(2, len(associated_move_line_ids))
        for move_line_id in associated_move_line_ids:
            self.assertEqual(self.env['account.move.line'].browse(move_line_id).move_id, right_move)

    def test__get_move_lines(self):
        journal = self._create_journal()
        normal_type = 'income'
        include_initial_balance_type = 'asset_receivable'

        # NORMAL ACCOUNT AND CONSO ACCOUNT
        normal_consolidation_account = self._create_consolidation_account()
        normal_account = self._create_account('NOR', 'Normal account', type=normal_type)
        normal_consolidation_account.write({'account_ids': [(4, normal_account.id)]})

        # INCLUDE ACCOUNT AND CONSO ACCOUNT
        include_consolidation_account = self._create_consolidation_account()
        include_initial_account = self._create_account('INC', 'Normal account', type=include_initial_balance_type)
        include_consolidation_account.write({'account_ids': [(4, include_initial_account.id)]})

        cp = self._create_company_period(start_date='2019-01-01', end_date='2019-12-31', company=self.default_company)

        # MOVES CREATION
        # move before begin date
        self._create_basic_move(9042, account_credit=normal_account, move_date=date(2012, 6, 30),
                                account_debit=include_initial_account, journal=journal, company=self.default_company)
        # move after begin date
        self._create_basic_move(42000, account_credit=normal_account, move_date=date(2019, 6, 30),
                                account_debit=include_initial_account, journal=journal, company=self.default_company)

        # NORMAL
        normal_domain = cp._get_move_lines_domain(normal_consolidation_account)
        normal_move_lines = self.env['account.move.line'].search(normal_domain)
        self.assertEqual(len(normal_move_lines), 1)

        # INCLUDE INITIAL BALANCE
        include_domain = cp._get_move_lines_domain(include_consolidation_account)
        include_move_lines = self.env['account.move.line'].search(include_domain)
        self.assertEqual(len(include_move_lines), 2)

    def test__convert(self):
        ap = self._create_analysis_period(start_date='2019-01-01', end_date='2019-01-31')
        cp = self._create_company_period(period=ap, start_date='2019-01-01', end_date='2019-01-31')
        rates = {'avg': 0.5, 'end': 0.35}
        cp.write({'currency_rate_avg': rates['avg'], 'currency_rate_end': rates['end']})

        amount = 15000
        self.assertAlmostEqual(cp._convert(amount, 'avg'), amount / rates['avg'])
        self.assertAlmostEqual(cp._convert(amount, 'end'), amount / rates['end'])
        self.assertAlmostEqual(cp._convert(amount, 'hist'), amount)
        self.assertAlmostEqual(cp._convert(amount, None), amount)

    def test__apply_consolidation_rate(self):
        cp = self._create_company_period(start_date='2019-01-01', end_date='2019-01-31', rate_consolidation=75.0)
        self.assertAlmostEqual(cp._apply_consolidation_rate(1000.0), 750.0)
