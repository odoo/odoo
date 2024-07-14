# -*- coding: utf-8 -*-
# pylint: disable=C0326
from freezegun import freeze_time

from .common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestTaxReportDefaultPart(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.revenue_1 = cls.company_data['default_account_revenue']
        cls.revenue_2 = cls.copy_account(cls.revenue_1)

        cls.report_generic = cls.env.ref('account.generic_tax_report')
        cls.report_grouped_account_tax = cls.env.ref('account.generic_tax_report_account_tax')
        cls.report_grouped_tax_account = cls.env.ref('account.generic_tax_report_tax_account')

    def checkAmlsRedirection(self, report, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict):
        # Check the caret options of the tax lines redirect to the correct amls
        for tax_line in tax_lines_with_caret_options:
            expected_amls = expected_amls_based_on_tax_dict.get(tax_line['name'])
            action = self.env[report.custom_handler_model_name].caret_option_audit_tax(options, {'line_id': tax_line['id']})
            domain = action['domain']
            actual_amls = self.env['account.move.line'].search(domain)
            self.assertEqual(set(actual_amls), set(expected_amls))

    def test_tax_affect_base(self):
        tax_20_affect_base = self.env['account.tax'].create({
            'name': "tax_20_affect_base",
            'amount_type': 'percent',
            'amount': 20.0,
            'include_base_amount': True,
            'type_tax_use': 'sale',
        })
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((tax_20_affect_base + tax_10).ids)],
                }),
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_2.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((tax_20_affect_base + tax_10).ids)],
                }),
            ],
        })
        invoice.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         640.0),
                ('tax_20_affect_base (20.0%)',          2000.0,     400.0),
                ('tax_10 (10.0%)',                      2400.0,     240.0),
                ('Total Sales',                         '',         640.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         640.0),
                ('400000 Product Sales',                '',         320.0),
                ('tax_20_affect_base (20.0%)',          1000.0,     200.0),
                ('tax_10 (10.0%)',                      1200.0,     120.0),
                ('Total 400000 Product Sales',          '',         320.0),
                ('400000.2 Product Sales',            '',         320.0),
                ('tax_20_affect_base (20.0%)',          1000.0,     200.0),
                ('tax_10 (10.0%)',                      1200.0,     120.0),
                ('Total 400000.2 Product Sales',      '',         320.0),
                ('Total Sales',                         '',         640.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         640.0),
                ('tax_20_affect_base (20.0%)',          '',         400.0),
                ('400000 Product Sales',                1000.0,     200.0),
                ('400000.2 Product Sales',            1000.0,     200.0),
                ('Total tax_20_affect_base (20.0%)',    '',         400.0),
                ('tax_10 (10.0%)',                      '',         240.0),
                ('400000 Product Sales',                1200.0,     120.0),
                ('400000.2 Product Sales',            1200.0,     120.0),
                ('Total tax_10 (10.0%)',                '',         240.0),
                ('Total Sales',                         '',         640.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_10 = invoice.line_ids.filtered(lambda x: x.tax_line_id == tax_10 or tax_10 in x.tax_ids)
        expected_amls_tax_20 = invoice.line_ids.filtered(lambda x: x.tax_line_id == tax_20_affect_base or tax_20_affect_base in x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_10 (10.0%)': expected_amls_tax_10,
            'tax_20_affect_base (20.0%)': expected_amls_tax_20,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_tax_group_shared_tax(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'none',
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'none',
        })
        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'type_tax_use': 'none',
        })
        tax_group_10_20 = self.env['account.tax'].create({
            'name': "tax_group_10_20",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10 + tax_20).ids)],
            'type_tax_use': 'sale',
        })
        tax_group_10_30 = self.env['account.tax'].create({
            'name': "tax_group_10_30",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10 + tax_30).ids)],
            'type_tax_use': 'sale',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_group_10_20.ids)],
                }),
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 2000.0,
                    'tax_ids': [Command.set(tax_group_10_30.ids)],
                }),
            ],
        })
        invoice.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         1100.0),
                ('tax_group_10_20',                     1000.0,     300.0),
                ('tax_group_10_30',                     2000.0,     800.0),
                ('Total Sales',                         '',         1100.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         1100.0),
                ('400000 Product Sales',                '',         1100.0),
                ('tax_group_10_20',                     1000.0,     300.0),
                ('tax_group_10_30',                     2000.0,     800.0),
                ('Total 400000 Product Sales',          '',         1100.0),
                ('Total Sales',                         '',         1100.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         1100.0),
                ('tax_group_10_20',                     '',         300.0),
                ('400000 Product Sales',                1000.0,     300.0),
                ('Total tax_group_10_20',               '',         300.0),
                ('tax_group_10_30',                     '',         800.0),
                ('400000 Product Sales',                2000.0,     800.0),
                ('Total tax_group_10_30',               '',         800.0),
                ('Total Sales',                         '',         1100.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_group_10_20 = invoice.line_ids.filtered(lambda x: x.group_tax_id == tax_group_10_20 or tax_group_10_20 in x.tax_ids)
        expected_amls_tax_group_10_30 = invoice.line_ids.filtered(lambda x: x.group_tax_id == tax_group_10_30 or tax_group_10_30 in x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_group_10_20': expected_amls_tax_group_10_20,
            'tax_group_10_30': expected_amls_tax_group_10_30,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

        # Same with tax_10 as a sale tax.
        tax_10.type_tax_use = 'sale'

        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         1100.0),
                ("tax_10 (10.0%)" ,                     3000.0,     300.0),
                ("tax_20 (20.0%)" ,                     1000.0,     200.0),
                ("tax_30 (30.0%)" ,                     2000.0,     600),
                ('Total Sales',                         '',         1100.0),
            ],
            options,
        )

        # Same with tax_20 as a sale tax.
        tax_10.type_tax_use = 'none'
        tax_20.type_tax_use = 'sale'

        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         1100.0),
                ("tax_10 (10.0%)" ,                     1000.0,     100.0),
                ("tax_20 (20.0%)" ,                     1000.0,     200.0),
                ('tax_group_10_30',                     2000.0,     800.0),
                ('Total Sales',                         '',         1100.0),
            ],
            options,
        )

    def test_tax_group_of_taxes_affected_by_other(self):
        tax_10_affect_base = self.env['account.tax'].create({
            'name': "tax_10_affect_base",
            'amount_type': 'percent',
            'amount': 10.0,
            'include_base_amount': True,
        })
        tax_20_affect_base = self.env['account.tax'].create({
            'name': "tax_20_affect_base",
            'amount_type': 'percent',
            'amount': 20.0,
            'include_base_amount': True,
            'type_tax_use': 'none',
        })
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'none',
        })
        tax_group = self.env['account.tax'].create({
            'name': "tax_group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_20_affect_base + tax_10).ids)],
            'type_tax_use': 'sale',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((tax_10_affect_base + tax_group).ids)],
                }),
            ],
        })
        invoice.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         452.0),
                ('tax_10_affect_base (10.0%)',          1000.0,     100.0),
                ('tax_group',                           1100.0,     352.0),
                ('Total Sales',                         '',         452.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         452.0),
                ('400000 Product Sales',                '',         452.0),
                ('tax_10_affect_base (10.0%)',          1000.0,     100.0),
                ('tax_group',                           1100.0,     352.0),
                ('Total 400000 Product Sales',          '',         452.0),
                ('Total Sales',                         '',         452.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         452.0),
                ('tax_10_affect_base (10.0%)',          '',         100.0),
                ('400000 Product Sales',                1000.0,     100.0),
                ('Total tax_10_affect_base (10.0%)',    '',         100.0),
                ('tax_group',                           '',         352.0),
                ('400000 Product Sales',                1100.0,     352.0),
                ('Total tax_group',                     '',         352.0),
                ('Total Sales',                         '',         452.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_10_affect_base = invoice.line_ids.filtered(lambda x: x.tax_line_id == tax_10_affect_base or tax_10_affect_base in x.tax_ids)
        expected_amls_tax_group = invoice.line_ids.filtered(lambda x: x.tax_line_id or x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_10_affect_base (10.0%)': expected_amls_tax_10_affect_base,
            'tax_group': expected_amls_tax_group,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_mixed_all_type_tax_use_same_line(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'purchase',
        })
        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'type_tax_use': 'none',
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))
        move_form.date = fields.Date.from_string('2019-01-01')
        with move_form.line_ids.new() as line_form:
            line_form.name = 'debit line'
            line_form.account_id = self.revenue_1
            line_form.debit = 1000.0
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax_10)
            line_form.tax_ids.add(tax_20)
            line_form.tax_ids.add(tax_30)
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit line'
            line_form.account_id = self.revenue_2
            line_form.credit = 1600
        move = move_form.save()
        move.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('tax_10 (10.0%)',                      -1000.0,    -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('tax_20 (20.0%)',                      1000.0,     200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('400000 Product Sales',                '',         -100.0),
                ('tax_10 (10.0%)',                      -1000.0,    -100.0),
                ('Total 400000 Product Sales',          '',         -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('400000 Product Sales',                '',         200.0),
                ('tax_20 (20.0%)',                      1000.0,     200.0),
                ('Total 400000 Product Sales',          '',         200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('tax_10 (10.0%)',                      '',         -100.0),
                ('400000 Product Sales',                -1000.0,    -100.0),
                ('Total tax_10 (10.0%)',                '',         -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('tax_20 (20.0%)',                      '',         200.0),
                ('400000 Product Sales',                1000.0,     200.0),
                ('Total tax_20 (20.0%)',                '',         200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_10 = move.line_ids.filtered(lambda x: x.tax_line_id == tax_10 or x.tax_ids)
        expected_amls_tax_20 = move.line_ids.filtered(lambda x: x.tax_line_id == tax_20 or x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_10 (10.0%)': expected_amls_tax_10,
            'tax_20 (20.0%)': expected_amls_tax_20,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_mixed_all_type_tax_on_different_line(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'purchase',
        })
        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'type_tax_use': 'none',
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))
        move_form.date = fields.Date.from_string('2019-01-01')
        for dummy in range(2):
            for tax in tax_10 + tax_20 + tax_30:
                with move_form.line_ids.new() as line_form:
                    line_form.name = 'debit line'
                    line_form.account_id = self.revenue_1
                    line_form.debit = 500.0
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(tax)
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit line'
            line_form.account_id = self.revenue_2
            line_form.credit = 3600
        move = move_form.save()
        move.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('tax_10 (10.0%)',                      -1000.0,    -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('tax_20 (20.0%)',                      1000.0,     200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('400000 Product Sales',                '',         -100.0),
                ('tax_10 (10.0%)',                      -1000.0,    -100.0),
                ('Total 400000 Product Sales',          '',         -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('400000 Product Sales',                '',         200.0),
                ('tax_20 (20.0%)',                      1000.0,     200.0),
                ('Total 400000 Product Sales',          '',         200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         -100.0),
                ('tax_10 (10.0%)',                      '',         -100.0),
                ('400000 Product Sales',                -1000.0,    -100.0),
                ('Total tax_10 (10.0%)',                '',         -100.0),
                ('Total Sales',                         '',         -100.0),
                ('Purchases',                           '',         200.0),
                ('tax_20 (20.0%)',                      '',         200.0),
                ('400000 Product Sales',                1000.0,     200.0),
                ('Total tax_20 (20.0%)',                '',         200.0),
                ('Total Purchases',                     '',         200.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_10 = move.line_ids.filtered(lambda x: x.tax_line_id == tax_10 or tax_10 in x.tax_ids)
        expected_amls_tax_20 = move.line_ids.filtered(lambda x: x.tax_line_id == tax_20 or tax_20 in x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_10 (10.0%)': expected_amls_tax_10,
            'tax_20 (20.0%)': expected_amls_tax_20,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_tax_report_custom_edition_tax_line(self):
        ''' When on a journal entry, a tax line is edited manually by the user, it could lead to a broken mapping
        between the original tax details and the edited tax line. In that case, some extra tax details are generated
        on the tax line in order to reflect this edition. This test is there to ensure the tax report is well handling
        such behavior.
        '''
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'sale',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((tax_10 + tax_20).ids)],
                }),
            ],
        })
        tax_10_line = invoice.line_ids.filtered(lambda x: x.tax_repartition_line_id.tax_id == tax_10)
        tax_20_line = invoice.line_ids.filtered(lambda x: x.tax_repartition_line_id.tax_id == tax_20)
        receivable_line = invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        invoice.write({'line_ids': [
            Command.update(tax_10_line.id, {'account_id': self.revenue_2.id}),
            Command.update(tax_20_line.id, {'account_id': self.revenue_2.id, 'credit': 201.0}),
            Command.update(receivable_line.id, {'debit': 1301.0}),
        ]})
        invoice.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         301.0),
                ('tax_10 (10.0%)',                      1000.0,     100.0),
                ('tax_20 (20.0%)',                      1000.0,     201.0),
                ('Total Sales',                         '',         301.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         301.0),
                ('400000 Product Sales',                '',         301.0),
                ('tax_10 (10.0%)',                      1000.0,     100.0),
                ('tax_20 (20.0%)',                      1000.0,     201.0),
                ('Total 400000 Product Sales',          '',         301.0),
                ('Total Sales',                         '',         301.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         301.0),
                ('tax_10 (10.0%)',                      '',         100.0),
                ('400000 Product Sales',                1000.0,     100.0),
                ('Total tax_10 (10.0%)',                '',         100.0),
                ('tax_20 (20.0%)',                      '',         201.0),
                ('400000 Product Sales',                1000.0,     201.0),
                ('Total tax_20 (20.0%)',                '',         201.0),
                ('Total Sales',                         '',         301.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls_tax_10 = invoice.line_ids.filtered(lambda x: x.tax_line_id == tax_10 or tax_10 in x.tax_ids)
        expected_amls_tax_20 = invoice.line_ids.filtered(lambda x: x.tax_line_id == tax_20 or tax_20 in x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax_10 (10.0%)': expected_amls_tax_10,
            'tax_20 (20.0%)': expected_amls_tax_20,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_tax_report_comparisons(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
        })
        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
        })

        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': inv_date,
            'date': inv_date,
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': account.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(taxes.ids)],
                }),
            ],
        } for inv_date, taxes, account in (
            ('2019-03-01', tax_10, self.revenue_1),
            ('2019-02-01', tax_20 + tax_30, self.revenue_2),
            ('2019-01-01', tax_30, self.revenue_1),
        )])
        invoices.action_post()

        date_from_str = '2019-03-01'
        date_to_str = '2019-03-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        options = self._update_comparison_filter(options, self.report_generic, 'previous_period', 2)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX         NET         TAX         NET         TAX
            [   0,                                      1,          2,          3,          4,          5,          6],
            [
                ('Sales',                                   '',     100.0,          '',     500.0,          '',     300.0),
                ('tax_10 (10.0%)',                      1000.0,     100.0,         0.0,       0.0,         0.0,       0.0),
                ('tax_20 (20.0%)',                         0.0,       0.0,      1000.0,     200.0,         0.0,       0.0),
                ('tax_30 (30.0%)',                         0.0,       0.0,      1000.0,     300.0,      1000.0,     300.0),
                ('Total Sales',                             '',     100.0,          '',     500.0,           '',    300.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        options = self._update_comparison_filter(options, self.report_grouped_account_tax, 'previous_period', 2)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX         NET         TAX         NET         TAX
            [   0,                                      1,          2,          3,          4,          5,          6],
            [
                ('Sales',                                   '',     100.0,          '',     500.0,          '',     300.0),
                ('400000 Product Sales',                    '',     100.0,          '',       0.0,          '',     300.0),
                ('tax_10 (10.0%)',                      1000.0,     100.0,         0.0,       0.0,         0.0,       0.0),
                ('tax_30 (30.0%)',                         0.0,       0.0,         0.0,       0.0,      1000.0,     300.0),
                ('Total 400000 Product Sales',              '',     100.0,          '',       0.0,          '',     300.0),
                ('400000.2 Product Sales',                  '',       0.0,          '',     500.0,          '',       0.0),
                ('tax_20 (20.0%)',                         0.0,       0.0,      1000.0,     200.0,         0.0,       0.0),
                ('tax_30 (30.0%)',                         0.0,       0.0,      1000.0,     300.0,         0.0,       0.0),
                ('Total 400000.2 Product Sales',            '',       0.0,          '',     500.0,          '',       0.0),
                ('Total Sales',                             '',     100.0,          '',     500.0,          '',     300.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        options = self._update_comparison_filter(options, self.report_grouped_tax_account, 'previous_period', 2)
        self.assertLinesValues(
            self.report_grouped_tax_account._get_lines(options),
            #   Name                                    NET         TAX         NET         TAX         NET         TAX
            [   0,                                      1,          2,          3,          4,          5,          6],
            [
                ('Sales',                                   '',     100.0,          '',     500.0,          '',     300.0),
                ('tax_10 (10.0%)',                          '',     100.0,          '',       0.0,          '',       0.0),
                ('400000 Product Sales',                1000.0,     100.0,         0.0,       0.0,         0.0,       0.0),
                ('Total tax_10 (10.0%)',                    '',     100.0,          '',       0.0,          '',       0.0),
                ('tax_20 (20.0%)',                          '',       0.0,          '',     200.0,          '',       0.0),
                ('400000.2 Product Sales',                 0.0,       0.0,      1000.0,     200.0,         0.0,       0.0),
                ('Total tax_20 (20.0%)',                    '',       0.0,          '',     200.0,          '',       0.0),
                ('tax_30 (30.0%)',                          '',       0.0,          '',     300.0,          '',     300.0),
                ('400000 Product Sales',                   0.0,       0.0,         0.0,       0.0,      1000.0,     300.0),
                ('400000.2 Product Sales',                 0.0,       0.0,      1000.0,     300.0,         0.0,       0.0),
                ('Total tax_30 (30.0%)',                    '',       0.0,          '',     300.0,          '',     300.0),
                ('Total Sales',                             '',     100.0,          '',     500.0,          '',     300.0),
            ],
            options,
        )

    def test_affect_base_with_repetitions(self):
        affecting_tax = self.env['account.tax'].create({
            'name': 'Affecting',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'include_base_amount': True,
            'sequence': 0,
            # We use default repartition: 1 base line, 1 100% tax line
        })

        affected_tax = self.env['account.tax'].create({
            'name': 'Affected',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'sequence': 1
            # We use default repartition: 1 base line, 1 100% tax line
        })

        # Create an invoice combining our taxes (1 line with each alone, and 1 line with both)
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2021-08-01',
            'invoice_line_ids': [
                Command.create({
                    'name': "affecting",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': affecting_tax.ids,
                }),

                Command.create({
                    'name': "affected",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': affected_tax.ids,
                }),

                Command.create({
                    'name': "affecting + affected",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': (affecting_tax + affected_tax).ids,
                }),
            ]
        })

        move.action_post()

        # Check generic tax report
        options = self._generate_options(self.report_generic, move.date, move.date)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                   Net              Tax
            [   0,                                       1,               2],
            [
                ("Sales",                               '',             108.2),
                ("%s (42.0%%)" % affecting_tax.name,   200,              84),
                ("%s (10.0%%)" % affected_tax.name,    242,              24.2),
                ("Total Sales",                         '',             108.2),
            ],
            options,
        )

    def test_tax_multiple_repartition_lines(self):
        tax = self.env['account.tax'].create({
            'name': "tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),

                Command.create({
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                }),
                Command.create({
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),

                Command.create({
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                }),
                Command.create({
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                }),
            ],
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         100.0),
                ('tax (10.0%)',                         1000.0,     100.0),
                ('Total Sales',                         '',         100.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         100.0),
                ('400000 Product Sales',                '',         100.0),
                ('tax (10.0%)',                         1000.0,     100.0),
                ('Total 400000 Product Sales',          '',         100.0),
                ('Total Sales',                         '',         100.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',         100.0),
                ('tax (10.0%)',                         '',         100.0),
                ('400000 Product Sales',                1000.0,     100.0),
                ('Total tax (10.0%)',                   '',         100.0),
                ('Total Sales',                         '',         100.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls = invoice.line_ids.filtered(lambda x: x.tax_line_id or x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax (10.0%)': expected_amls,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    @freeze_time('2019-01-01')
    def test_tax_invoice_completely_refund(self):
        tax = self.env['account.tax'].create({
            'name': "tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'base line',
                    'account_id': self.revenue_1.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=invoice.ids)\
            .create({
                'reason': "test_tax_invoice_completely_refund",
                'journal_id': invoice.journal_id.id,
            })\
            .modify_moves()

        date_from_str = '2019-01-01'
        date_to_str = '2019-01-31'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',        0.0),
                ('tax (10.0%)',                        0.0,        0.0),
                ('Total Sales',                         '',        0.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',        0.0),
                ('400000 Product Sales',                '',        0.0),
                ('tax (10.0%)',                        0.0,        0.0),
                ('Total 400000 Product Sales',          '',        0.0),
                ('Total Sales',                         '',        0.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET         TAX
            [   0,                                      1,          2],
            [
                ('Sales',                               '',        0.0),
                ('tax (10.0%)',                         '',        0.0),
                ('400000 Product Sales',               0.0,        0.0),
                ('Total tax (10.0%)',                   '',        0.0),
                ('Total Sales',                         '',        0.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls = invoice.line_ids.filtered(lambda x: x.tax_line_id or x.tax_ids) + invoice.reversal_move_id.line_ids.filtered(lambda x: x.tax_line_id or x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax (10.0%)': expected_amls,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)

    def test_tax_report_entry_move_2_opposite_invoice_lines(self):
        tax = self.env['account.tax'].create({
            'name': "tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
        })

        # Form is used here for the dynamic tax line to get created automatically
        move_form = Form(self.env['account.move']\
                         .with_context(default_move_type='entry'))
        # {'invisible': [('move_type', 'not in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'])]
        move_form.date = '2022-02-01'

        for name, account_id, debit, credit, tax_to_apply in (
                ("invoice line in entry", self.company_data['default_account_revenue'], 0.0, 20.0, tax),
                ("refund line in entry", self.company_data['default_account_revenue'], 10.0, 0.0, tax),
                ("Receivable line in entry", self.company_data['default_account_receivable'], 11.0, 0.0, None),
        ):
            with move_form.line_ids.new() as line_form:
                line_form.name = name
                line_form.account_id = account_id
                line_form.debit = debit
                line_form.credit = credit
                if tax_to_apply:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(tax_to_apply)

        move = move_form.save()
        move.action_post()

        date_from_str = '2022-02-01'
        date_to_str = '2022-02-01'
        options = self._generate_options(self.report_generic, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_generic._get_lines(options),
            #   Name                                    NET           TAX
            [   0,                                      1,             2],
            [
                ('Sales',                               '',          1.0),
                ('tax (10.0%)',                       10.0,          1.0),
                ('Total Sales',                         '',          1.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_account_tax, date_from_str, date_to_str)
        self.assertLinesValues(
            self.report_grouped_account_tax._get_lines(options),
            #   Name                                    NET           TAX
            [   0,                                      1,             2],
            [
                ('Sales',                               '',          1.0),
                ('400000 Product Sales',                '',          1.0),
                ('tax (10.0%)',                       10.0,          1.0),
                ('Total 400000 Product Sales',          '',          1.0),
                ('Total Sales',                         '',          1.0),
            ],
            options,
        )

        options = self._generate_options(self.report_grouped_tax_account, date_from_str, date_to_str)
        report_lines = self.report_grouped_tax_account._get_lines(options)
        self.assertLinesValues(
            report_lines,
            #   Name                                    NET            TAX
            [   0,                                      1,              2],
            [
                ('Sales',                               '',           1.0),
                ('tax (10.0%)',                         '',           1.0),
                ('400000 Product Sales',              10.0,           1.0),
                ('Total tax (10.0%)',                   '',           1.0),
                ('Total Sales',                         '',           1.0),
            ],
            options,
        )

        tax_lines_with_caret_options = [report_line for report_line in report_lines if report_line.get('caret_options') == 'generic_tax_report']
        expected_amls = move.line_ids.filtered(lambda x: x.tax_line_id or x.tax_ids)
        expected_amls_based_on_tax_dict = {
            'tax (10.0%)': expected_amls,
        }
        self.checkAmlsRedirection(self.report_grouped_tax_account, options, tax_lines_with_caret_options, expected_amls_based_on_tax_dict)
