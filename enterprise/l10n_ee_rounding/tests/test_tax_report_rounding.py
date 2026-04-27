from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEstonianFiscalRounding(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('ee')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_ee = cls.env['res.partner'].create({
            'name': 'Partner EE 1',
            'country_id': cls.env.ref('base.ee').id,
            'company_registry': '98765432',
            'vat': 'EE023456783',
            'is_company': True,
        })

        # sales VAT
        cls.vat_out_22_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_22_g')
        cls.vat_out_20_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_20_g')
        cls.vat_out_9_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_9_g')
        cls.vat_out_5_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_5_g')

        # accounts
        cls.vat_payable = cls.env['account.chart.template'].ref('l10n_ee_201204')
        cls.difference_loss_acc = cls.company_data['company'].l10n_ee_rounding_difference_loss_account_id
        cls.difference_profit_acc = cls.company_data['company'].l10n_ee_rounding_difference_profit_account_id

        cls.report = cls.env.ref('l10n_ee.tax_report').with_company(cls.company_data['company'])
        cls.handler = cls.env['l10n_ee.tax.report.handler']

        cls._standard_line_dict = {
            'name': 'Line1',
            'price_unit': 900.99,
            'quantity': 1,
            'tax_ids': [Command.set(cls.vat_out_22_g.ids)],
        }

        cls._standard_invoice_dict = {
            'move_type': 'out_invoice',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'partner_id': cls.partner_ee.id,
            'invoice_date': '2024-05-11',
            'date': '2024-05-11',
            'invoice_line_ids': [Command.create(cls._standard_line_dict)],
        }

    def test_l10n_ee_closing_entry_individual_tax_rounding(self):
        """ The Estonian government, and thus the tax report, computes total sales tax as
            base_amount * tax_rate, while Odoo rounds taxes on an invoice line level. This
            difference in when the rounding happens can lead to a difference between the tax
            amount computed by Odoo and the sales tax informed in the report.
        """
        invoice_dict = {
            **self._standard_invoice_dict,
            'invoice_line_ids': [
                Command.create({**self._standard_line_dict, 'price_unit': 100.01}),
            ]
        }
        invoice_dicts = [invoice_dict.copy() for _i in range(5)]
        self.env['account.move'].create(invoice_dicts).action_post()

        # Odoo calculates the tax as 5 (number of invoices) * rounded result of 22% of 100.01 = 110.
        # Tax value reported is the rounded result of 5 * 100.01 (base amount) * 22%. This results in a rounding cost of 0.01.
        expected_closing_entry_lines = [
            Command.create({'name': '22% G', 'debit': 110.0, 'credit': 0, 'account_id': self.vat_payable.id}),
            Command.create({'name': 'Difference from rounding taxes', 'debit': 0.01, 'credit': 0, 'account_id': self.difference_loss_acc.id}),
        ]

        options = self._generate_options(self.report, '2024-05-01', '2024-05-31')
        lines, _tax_subtotals = self.handler._compute_vat_closing_entry(self.company_data['company'], options)
        self.assertEqual(lines, expected_closing_entry_lines)

    def test_l10n_ee_closing_entry_multiple_taxes_rounding(self):
        """ The total base amount is multiplied by the different tax rates and then summed up in
            line 4 of the tax report. Hence, only one line of rounding should be added to the
            closing entry even if multiple sale tax rates apply.
        """
        invoice_dict = {
            **self._standard_invoice_dict,
            'invoice_line_ids': [
                Command.create(self._standard_line_dict),
                Command.create({**self._standard_line_dict, 'tax_ids': [Command.set(self.vat_out_20_g.ids)]}),
                Command.create({**self._standard_line_dict, 'tax_ids': [Command.set(self.vat_out_9_g.ids)]}),
                Command.create({**self._standard_line_dict, 'tax_ids': [Command.set(self.vat_out_5_g.ids)]}),
            ]
        }
        invoice_dicts = [invoice_dict.copy() for _i in range(5)]
        self.env['account.move'].create(invoice_dicts).action_post()
        # Odoo calculates the tax as 2522.8 and tax value reported is 2522.77, resulting in a rounding profit of 0.03.
        expected_closing_entry_lines = [
            Command.create({'name': '20% G', 'debit': 901.0, 'credit': 0, 'account_id': self.vat_payable.id}),
            Command.create({'name': '22% G', 'debit': 991.1, 'credit': 0, 'account_id': self.vat_payable.id}),
            Command.create({'name': '9% G', 'debit': 405.45, 'credit': 0, 'account_id': self.vat_payable.id}),
            Command.create({'name': '5% G', 'debit': 225.25, 'credit': 0, 'account_id': self.vat_payable.id}),
            Command.create({'name': 'Difference from rounding taxes', 'debit': 0, 'credit': 0.03, 'account_id': self.difference_profit_acc.id}),
        ]

        options = self._generate_options(self.report, '2024-05-01', '2024-05-31')
        lines, _tax_subtotals = self.handler._compute_vat_closing_entry(self.company_data['company'], options)
        self.assertEqual(lines, expected_closing_entry_lines)
