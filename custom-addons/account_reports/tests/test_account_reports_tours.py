# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=C0326

from odoo import Command

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

@tagged('post_install', '-at_install')
class TestAccountReportsTours(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.report = cls.env.ref('account_reports.balance_sheet')
        cls.report.column_ids.sortable = True

        # Create moves
        cls.account_101401 = cls.env['account.account'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 101401)
        ])

        cls.account_101402 = cls.env['account.account'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 101402)
        ])

        cls.account_101404 = cls.env['account.account'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 101404)
        ])

        cls.account_121000 = cls.env['account.account'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 121000)
        ])

        cls.account_251000 = cls.env['account.account'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('code', '=', 251000)
        ])

        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2022-06-01',
            'journal_id': cls.company_data['default_journal_cash'].id,
            'line_ids': [
                (0, 0, {'debit':  75.0,     'credit':   0.0,    'account_id': cls.account_101401.id}),
                (0, 0, {'debit': 100.0,     'credit':   0.0,    'account_id': cls.account_101402.id}),
                (0, 0, {'debit':  50.0,     'credit':   0.0,    'account_id': cls.account_101404.id}),
                (0, 0, {'debit':  25.0,     'credit':   0.0,    'account_id': cls.account_121000.id}),
                (0, 0, {'debit':   0.0,     'credit': 250.0,    'account_id': cls.account_251000.id}),
            ],
        })

        move.action_post()

        # Line ids
        line_id_ta = cls.report._get_generic_line_id('account.report.line', cls.env.ref('account_reports.account_financial_report_total_assets0').id)
        line_id_ca = cls.report._get_generic_line_id('account.report.line', cls.env.ref('account_reports.account_financial_report_current_assets_view0').id, parent_line_id=line_id_ta)
        line_id_ba = cls.report._get_generic_line_id('account.report.line', cls.env.ref('account_reports.account_financial_report_bank_view0').id, parent_line_id=line_id_ca)
        line_id_101401 = cls.report._get_generic_line_id('account.account', cls.account_101401.id, markup='groupby:account_id', parent_line_id=line_id_ba)
        line_id_cas = cls.report._get_generic_line_id('account.report.line', cls.env.ref('account_reports.account_financial_report_current_assets0').id, parent_line_id=line_id_ca)
        line_id_101404 = cls.report._get_generic_line_id('account.account', cls.account_101404.id, markup='groupby:account_id', parent_line_id=line_id_cas)

        # Create footnotes
        cls.report.write({
            'footnotes_ids': [
                Command.create({
                    'line_id': line_id_101401,
                    'text': 'Footnote 101401',
                }),
                Command.create({
                    'line_id': line_id_101404,
                    'text': 'Footnote 101404',
                }),
            ]
        })

    def test_account_reports_tours(self):
        self.start_tour("/web", 'account_reports', login=self.env.user.login)
