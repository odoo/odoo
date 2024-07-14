# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestTourAccountAnalyticFilters(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id += cls.env.ref(
            'analytic.group_analytic_accounting')
        cls.report = cls.env.ref('account_reports.profit_and_loss')
        cls.report.write({'filter_analytic': True})
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.env['account.analytic.account'].create({
            'name': 'Time Off',
            'plan_id': cls.analytic_plan.id
        })

    def test_tour_account_report_analytic_filters(self):
        self.start_tour("/web", 'account_reports_analytic_filters', login=self.env.user.login)
