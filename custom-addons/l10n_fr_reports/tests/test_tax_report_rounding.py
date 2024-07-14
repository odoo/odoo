# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrenchFiscalRounding(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # purchase and sales VAT
        cls.tva_20_percent_vente = cls.env.ref(f"account.{cls.company_data['company'].id}_tva_normale")
        cls.tva_20_percent_ttc_vente = cls.env.ref(f"account.{cls.company_data['company'].id}_tva_normale_ttc")
        cls.tva_20_percent_achat = cls.env.ref(f"account.{cls.company_data['company'].id}_tva_acq_normale")
        cls.tva_8pt5_percent_vente = cls.env.ref(f"account.{cls.company_data['company'].id}_tva_specifique")

        # accounts
        cls.tva_collected = cls.env.ref(f"account.{cls.company_data['company'].id}_pcg_44571")
        cls.tva_deductible = cls.env.ref(f"account.{cls.company_data['company'].id}_pcg_44566")
        cls.difference_loss_acc = cls.company_data['company'].l10n_fr_rounding_difference_loss_account_id
        cls.difference_profit_acc = cls.company_data['company'].l10n_fr_rounding_difference_profit_account_id

        cls.report = cls.env.ref('l10n_fr.tax_report').with_company(cls.company_data['company'])
        cls.handler = cls.env['l10n_fr.report.handler']

        cls._standard_line_dict = {
            'name': 'In-Sewer-Ants-Polly-Sea',
            'price_unit': 123.45,
            'quantity': 1,
            'tax_ids': [(6, 0, cls.tva_20_percent_vente.ids)],
        }

        cls._standard_invoice_dict = {
            'move_type': 'out_invoice',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'partner_id': cls.partner_a.id,
            'invoice_date': '2021-05-11',
            'date': '2021-05-11',
            'invoice_line_ids': [(0, 0, cls._standard_line_dict)],
        }
    def test_closing_entry_individual_tax_roundings(self):
        """ Each tax should be rounded according to the line of the report it appears on.
            For instance the payable taxes appear on individual lines depending on the rate,
            (20%, 10%, 8.5%, etc.) whereas the purchase taxes appear on a few lines of the
            report that don't correspond to the rates, tax groups, or individual taxes
            (e.g. 20 - Autres bien et services)
        """
        invoice_dict = {
            **self._standard_invoice_dict,
            'invoice_line_ids': [
                (0, 0, self._standard_line_dict),
                (0, 0, {**self._standard_line_dict, 'quantity': 2, 'tax_ids': [(6, 0, self.tva_8pt5_percent_vente.ids)]}),
            ]
        }
        options = self._generate_options(self.report, '2021-05-01', '2021-05-31')
        self.env['account.move'].create(invoice_dict).action_post()
        # In this case, each tax report line is rounded up, resulting in a rounding cost of 0.31 + 0.01 = 0.32.
        expected_closing_entry_lines = [
            (0, 0, {'name': '20% G', 'debit': 24.69, 'credit': 0, 'account_id': self.tva_collected.id}),
            (0, 0, {'name': '8.5% G', 'debit': 20.99, 'credit': 0, 'account_id': self.tva_collected.id}),
            (0, 0, {'name': 'Difference from rounding taxes', 'debit': 0.32, 'credit': 0, 'account_id': self.difference_loss_acc.id}),
        ]
        lines, _ = self.handler._compute_vat_closing_entry(self.company_data['company'], options)
        self.assertEqual(lines, expected_closing_entry_lines)

    def test_closing_entry_tax_belonging_to_same_line_rounding(self):
        """ A tax like 20% TVA and 20% TVA TTC appear on the same line of the report, and thus should not
            be rounded individually
        """
        invoice_dict = {
            **self._standard_invoice_dict,
            'invoice_line_ids': [
                (0, 0, {**self._standard_line_dict, 'tax_ids': [(6, 0, self.tva_20_percent_vente.ids)]}),
                (0, 0, {**self._standard_line_dict, 'tax_ids': [(6, 0, self.tva_20_percent_ttc_vente.ids)]}),
            ],
        }
        options = self._generate_options(self.report, '2021-05-01', '2021-05-31')
        self.env['account.move'].create(invoice_dict).action_post()

        # We expect one row for each tax, but the rounding should be on the some of the taxes, since they
        # both correspond to the same report line
        expected_closing_entry_lines = [
            (0, 0, {'name': '20% G', 'debit': 24.69, 'credit': 0, 'account_id': self.tva_collected.id}),
            (0, 0, {'name': '20% G INC', 'debit': 20.57, 'credit': 0, 'account_id': self.tva_collected.id}),
            (0, 0, {'name': 'Difference from rounding taxes', 'debit': 0, 'credit': 0.26, 'account_id': self.difference_profit_acc.id}),
        ]
        lines, _ = self.handler._compute_vat_closing_entry(self.company_data['company'], options)
        self.assertEqual(lines, expected_closing_entry_lines)

    def test_closing_entry_tax_deductible_rounding_and_carryover(self):
        """ When the tax is a deductible, a rounding down is equivalent to a loss, and a rounding up
            is equivalent to a profit. The deductible taxes should be rounded in the carryover line too.
        """
        # In this case 20% of 123.45 is about 24.69, which should be rounded up by around 31 cents
        bill_dict = {
            **self._standard_invoice_dict,
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [
                (0, 0, {**self._standard_line_dict, 'tax_ids': [(6, 0, self.tva_20_percent_achat.ids)]})
            ]
        }
        options = self._generate_options(self.report, '2021-05-01', '2021-05-31')
        move = self.env['account.move'].create(bill_dict)
        move.action_post()
        expected_closing_entry_lines = [
            (0, 0, {'name': '20% G', 'debit': 0, 'credit': 24.69, 'account_id': self.tva_deductible.id}),
            # Since the credit is being rounded up, the total difference credited increases
            (0, 0, {'name': 'Difference from rounding taxes', 'debit': 0, 'credit': 0.31, 'account_id': self.difference_profit_acc.id}),
        ]
        lines, _ = self.handler._compute_vat_closing_entry(self.company_data['company'], options)
        self.assertEqual(lines, expected_closing_entry_lines)

        carryover_line_id = self.env.ref('l10n_fr.tax_report_27').id
        options = self._generate_options(self.report, '2021-05-01', '2021-05-31')
        report_lines = self.report._get_lines(options)
        carryover_line, = [line for line in report_lines if line['columns'][0]['report_line_id'] == carryover_line_id]
        self.assertEqual(25.00, carryover_line['columns'][0]['no_format'])

        # Suppress the pdf output
        with patch.object(type(move), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            closing_move = self.handler._generate_tax_closing_entries(self.report, options)
            closing_move._post()

        options = self._generate_options(self.report, '2021-06-01', '2021-06-30')
        report_lines = self.report._get_lines(options)
        carryover_line, = [line for line in report_lines if line['columns'][0]['report_line_id'] == carryover_line_id]
        self.assertEqual(25.00, carryover_line['columns'][0]['no_format'])
