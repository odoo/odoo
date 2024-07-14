# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase


@tagged('post_install', '-at_install')
class TestAccountConsolidationChart(AccountConsolidationTestCase):
    # TESTS
    def test_account_ids_count(self):
        count = 5
        for i in range(count):
            self._create_consolidation_account(chart=self.chart)

        chart = self.env['consolidation.chart'].create({'name': 'bluh', 'currency_id': self.env.ref('base.EUR').id})
        self._create_consolidation_account(chart=chart)
        self.assertEqual(count, self.chart.account_ids_count)
        self.assertEqual(1, chart.account_ids_count)

    def test_period_ids_count(self):
        count = 5
        for i in range(count):
            self._create_analysis_period(chart=self.chart)
        chart = self.env['consolidation.chart'].create({'name': 'bluh', 'currency_id': self.env.ref('base.EUR').id})
        self._create_analysis_period(chart=chart)
        self.assertEqual(count, self.chart.period_ids_count)
        self.assertEqual(1, chart.period_ids_count)

    def test_unlink(self):
        Account = self.env['consolidation.account']
        AnalysisPeriod = self.env['consolidation.period']
        chart = self.env['consolidation.chart'].create({'name': 'bluh', 'currency_id': self.env.ref('base.EUR').id})
        acc = self._create_consolidation_account(chart=chart)
        ap = self._create_analysis_period(chart=chart)
        self.assertEqual(Account.search_count([('id', '=', acc.id)]), 1)
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap.id)]), 1)

        chart.unlink()

        self.assertEqual(Account.search_count([('id', '=', acc.id)]), 0)
        self.assertEqual(AnalysisPeriod.search_count([('id', '=', ap.id)]), 0)

    def test_copy_consolidation_chart(self):
        # Test that copying a chart is properly copying every accounts, groups,... and linking them to the new chart
        base_chart = self.env['consolidation.chart'].create({'name': 'Base Chart', 'currency_id': self.env.ref('base.EUR').id})
        group_a = self.env['consolidation.group'].create({
            'chart_id': base_chart.id,
            'name': 'Group A',
            'sequence': 1,
        })
        group_b, group_aa, group_ab = self.env['consolidation.group'].create([{
            'chart_id': base_chart.id,
            'name': 'Group B',
            'sequence': 2,
        }, {
            'chart_id': base_chart.id,
            'parent_id': group_a.id,
            'name': 'Group AA',
            'sequence': 3,
        }, {
            'chart_id': base_chart.id,
            'parent_id': group_a.id,
            'name': 'Group AB',
            'sequence': 4,
        }])
        group_aaa = self.env['consolidation.group'].create({
            'chart_id': base_chart.id,
            'parent_id': group_aa.id,
            'name': 'Group AAA',
            'sequence': 5,
        })
        self.env['consolidation.account'].create([{
            'chart_id': base_chart.id,
            'name': 'Account BA',
            'currency_mode': 'end',
            'group_id': group_b.id,
        }, {
            'chart_id': base_chart.id,
            'name': 'Account AAAA',
            'currency_mode': 'end',
            'group_id': group_aaa.id,
        }, {
            'chart_id': base_chart.id,
            'name': 'Account AAAB',
            'currency_mode': 'end',
            'group_id': group_aaa.id,
        }, {
            'chart_id': base_chart.id,
            'name': 'Account ABA',
            'currency_mode': 'end',
            'group_id': group_ab.id,
        }, {
            'chart_id': base_chart.id,
            'name': 'Account X',
            'currency_mode': 'end',
        }])
        copied_chart = base_chart.copy()
        copied_group_a, copied_group_b, copied_group_aa, copied_group_ab, copied_group_aaa = copied_chart.group_ids.sorted(lambda g: g.sequence)
        # Check that all four groups where properly copied and are linked to the chart ids.
        for base_group, copied_group in zip(base_chart.group_ids.sorted(lambda g: g.sequence), copied_chart.group_ids.sorted(lambda g: g.sequence)):
            self.assertEqual(copied_group.name, f'{base_group.name} (copy)')

        # Also make sure that all children groups have the right parents.
        for parent_group, copied_group in zip([copied_group_a, copied_group_a, copied_group_aa], [copied_group_aa, copied_group_ab, copied_group_aaa]):
            self.assertEqual(copied_group.parent_id, parent_group)

        # Ensure that all accounts were copied and are linked to the chart
        for base_account, copied_account in zip(base_chart.account_ids.sorted(lambda a: a.name), copied_chart.account_ids.sorted(lambda a: a.name)):
            self.assertEqual(copied_account.name, f'{base_account.name} (copy)')

        # Make sure that all copied accounts are linked to their groups too
        expected_groups_for_accounts = [self.env['consolidation.group'], copied_group_b, copied_group_aaa, copied_group_aaa, copied_group_ab]
        for copied_group, copied_account in zip(expected_groups_for_accounts, copied_chart.account_ids):
            self.assertEqual(copied_account.group_id, copied_group)


@tagged('post_install', '-at_install')
class TestAccountConsolidationAccount(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        ConsoChart = self.env['consolidation.chart']
        self.mapped_account = self._create_consolidation_account('I am mapped', chart=self.chart, section=None)

        self.not_mapped_account = self._create_consolidation_account('I am not mapped', chart=self.chart, section=None)

        self.super_charts = [
            ConsoChart.create({'name': 'blah', 'currency_id': self.env.ref('base.EUR').id}),
            ConsoChart.create({'name': 'bluh', 'currency_id': self.env.ref('base.EUR').id})
        ]
        self.super_accounts = [
            self._create_consolidation_account('I am the mapping one %s' % sc.id, chart=sc, section=None)
            for sc in self.super_charts
        ]
        self.mapped_account.write({'used_in_ids': [(6, 0, [sa.id for sa in self.super_accounts])]})

    # TESTS
    def test_filtered_used_in_ids_removal(self):
        context_chart = self.super_charts[0]
        ConsoAccountCtx = self.env['consolidation.account'].with_context(chart_id=context_chart.id)

        # Removed all mapped accounts with a chart in context
        ConsoAccountCtx.browse(self.mapped_account.id).write({'filtered_used_in_ids': [(6, 0, [])]})

        # The records linked to context chart are removed
        mapped_charts = {ma.chart_id for ma in self.mapped_account.used_in_ids}
        self.assertNotIn(context_chart, mapped_charts)

        # Only the records linked to context chart are removed
        for chart in self.super_charts[1:]:
            if chart != context_chart:
                self.assertIn(chart, mapped_charts)

    def test_filtered_used_in_ids_search(self):
        # TESTING THE SEARCH
        ConsoAccountCharts = [self.env['consolidation.account'].with_context(chart_id=sc.id)
                              for sc in self.super_charts]
        for i, ConsoAccountChart in enumerate(ConsoAccountCharts):
            not_mappeds = ConsoAccountChart.search([
                ('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '=', False)
            ])
            mappeds = ConsoAccountChart.search([
                ('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '!=', False)
            ])
            self.assertEqual(not_mappeds, self.not_mapped_account)
            self.assertEqual(mappeds, self.mapped_account)

    def test_filtered_used_in_ids(self):
        ConsoAccount = self.env['consolidation.account']
        # TESTING THE COMPUTING
        self.assertEqual(len(ConsoAccount.browse(self.mapped_account.id).used_in_ids), 2)

        for sc in self.super_charts:
            consolidation_account = ConsoAccount.with_context(chart_id=sc.id).browse(self.mapped_account.id)
            self.assertEqual(len(consolidation_account.filtered_used_in_ids), 1)
            self.assertEqual(len(consolidation_account.used_in_ids), len(self.super_accounts))

        # TESTING THE WRITING
        new_super_account = self._create_consolidation_account('New super account', chart=self.super_charts[0])
        self.mapped_account.with_context(chart_id=self.super_charts[0].id).filtered_used_in_ids += new_super_account

        # - context of first super chart --> should be mapped twice
        self.assertEqual(len(self.mapped_account.with_context(chart_id=self.super_charts[0].id).filtered_used_in_ids),
                         2,
                         'With first super chart context, mapped_account should be mapped twice to chart')
        self.assertEqual(len(self.mapped_account.with_context(chart_id=self.super_charts[0].id).used_in_ids),
                         len(self.super_accounts) + 1,
                         'With first super chart context, mapped_account should be mapped thrice')

        # - context of second super chart --> should be mapped once
        self.assertEqual(len(self.mapped_account.with_context(chart_id=self.super_charts[1].id).filtered_used_in_ids),
                         1,
                         'With second super chart context, mapped_account should be mapped once to chart')
        self.assertEqual(len(self.mapped_account.with_context(chart_id=self.super_charts[1].id).used_in_ids),
                         len(self.super_accounts) + 1,
                         'With second super chart context, mapped_account should be mapped thrice')

        # MAP ACCOUNT in chart 1
        self.not_mapped_account.write({
            'used_in_ids': [(6, 0, self.super_accounts[0].ids)]
        })

        # ACCOUNT IS NOW CONSIDERED AS MAPPED FOR CHART 1
        # BUT NOTHING CHANGE FOR OTHER CHARTS

        # - context of first super chart
        self.assertEqual(
            self.mapped_account.with_context(chart_id=self.super_charts[0].id).search_count([
                ('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '=', False)]),
            0)
        self.assertEqual(
            self.mapped_account.with_context(chart_id=self.super_charts[0].id).search_count([
                ('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '!=', False)]),
            2)

        # - context of second super chart
        second_super_chart_not_mappeds = self.mapped_account.with_context(chart_id=self.super_charts[1].id).search(
            [('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '=', False)])
        second_super_chart_mappeds = self.mapped_account.with_context(chart_id=self.super_charts[1].id).search(
            [('chart_id', '=', self.chart.id), ('filtered_used_in_ids', '!=', False)])
        self.assertEqual(len(second_super_chart_not_mappeds), 1)
        self.assertEqual(len(second_super_chart_mappeds), 1)
        self.assertEqual(second_super_chart_not_mappeds[0].id, self.not_mapped_account.id)
        self.assertEqual(second_super_chart_mappeds[0].id, self.mapped_account.id)

    def test_filtered_consolidation_account_ids(self):
        mapped_account = self._create_account('001', 'RCV', company=self.default_company)
        account_not_mapped = self._create_account('002', 'RCV2', company=self.default_company)

        chart_2 = self.env['consolidation.chart'].create({
            'name': 'blah',
            'currency_id': self.env.ref('base.EUR').id,
            'company_ids': [(6, 0, (self.us_company.id, self.default_company.id))]
        })

        conso_accounts = [
            self._create_consolidation_account('Chart 1 BLAH 1', chart=self.chart, section=None),
            self._create_consolidation_account('Chart 1 BLAH 2', chart=self.chart, section=None),
            self._create_consolidation_account('Chart 1 BLAH 3', chart=self.chart, section=None),
            self._create_consolidation_account('Chart 2 BLAH 1', chart=chart_2, section=None),
            self._create_consolidation_account('Chart 2 BLAH 2', chart=chart_2, section=None)
        ]

        mapped_account.write({'consolidation_account_ids': [(6, 0, [ca.id for ca in conso_accounts])]})
        self.assertEqual(len(mapped_account.consolidation_account_ids), len(conso_accounts))

        # TESTING THE COMPUTING
        AccountChart1 = self.env['account.account'].with_context(chart_id=self.chart.id)
        account_c1 = AccountChart1.browse(mapped_account.id)
        self.assertEqual(len(account_c1.consolidation_account_chart_filtered_ids), 3)
        self.assertEqual(len(account_c1.consolidation_account_ids), len(conso_accounts))

        AccountChart2 = self.env['account.account'].with_context(chart_id=chart_2.id)
        account_c2 = AccountChart2.browse(mapped_account.id)
        self.assertEqual(len(account_c2.consolidation_account_chart_filtered_ids), 2)
        self.assertEqual(len(account_c2.consolidation_account_ids), len(conso_accounts))

        # TESTING THE WRITING
        new_conso_account = self._create_consolidation_account('Chart 1 BLAH 1', chart=self.chart, section=None)
        account_c1.write({
            'consolidation_account_chart_filtered_ids': [(4, new_conso_account.id)]
        })
        account_c1 = AccountChart1.browse(mapped_account.id)

        self.assertEqual(len(account_c1.consolidation_account_chart_filtered_ids), 4)
        self.assertEqual(len(account_c1.consolidation_account_ids), len(conso_accounts) + 1)

        total_amount_of_account = self.env['account.account'].search_count([])
        amount_of_unmapped_account = total_amount_of_account - 1
        # TESTING THE SEARCH
        for Account in AccountChart1, AccountChart2:
            not_mappeds = Account.search([('consolidation_account_chart_filtered_ids', '=', False)])
            self.assertEqual(len(not_mappeds), amount_of_unmapped_account)
            self.assertIn(account_not_mapped.id, not_mappeds.ids)
            mappeds = Account.search([('consolidation_account_chart_filtered_ids', '!=', False)])
            self.assertEqual(len(mappeds), 1)
            self.assertEqual(mappeds[0].id, mapped_account.id)

        # MAP ACCOUNT in chart 1
        account_not_mapped.write({
            'consolidation_account_ids': [(6, 0, conso_accounts[0].ids)]
        })

        # ACCOUNT IS NOW CONSIDERED AS MAPPED FOR CHART 1
        not_mappeds = AccountChart1.search([('consolidation_account_chart_filtered_ids', '=', False)])
        self.assertEqual(len(not_mappeds), amount_of_unmapped_account - 1)
        mappeds = AccountChart1.search([('consolidation_account_chart_filtered_ids', '!=', False)])
        self.assertEqual(len(mappeds), 2)
        self.assertSetEqual(set(mappeds.ids), {account_not_mapped.id, mapped_account.id})

        # NOTHING CHANGE FOR CHART 2
        not_mappeds = AccountChart2.search([('consolidation_account_chart_filtered_ids', '=', False)])
        self.assertEqual(len(not_mappeds), amount_of_unmapped_account)
        self.assertIn(account_not_mapped.id, not_mappeds.ids)
        mappeds = AccountChart2.search([('consolidation_account_chart_filtered_ids', '!=', False)])
        self.assertEqual(len(mappeds), 1)
        self.assertEqual(mappeds[0].id, mapped_account.id)
