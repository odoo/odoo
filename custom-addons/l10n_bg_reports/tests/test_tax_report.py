# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=C0326

from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class BulgarianTaxReportTest(TestAccountReportsCommon):
    """ Bulgarian tax report explained:
        The amount of vat that could be paid (from invoices) is done in line 50, and the amount of vat that could be
        refunded (from bills) is done in line 60.

        Every month, the user has to do a closing entry and pay the vat amount that he owes the state. That is done
        in line 71. If the user is entitled to a vat refund from previous periods, the amount he has to pay will
        instead be deducted from that. That is done in line 70.

        Every 3 months, the user asks for a vat refund from the state by putting the expected amount in lines 80,
        81 or 82. At that point, everything starts over for a period of 3 months.
    """
    @classmethod
    def setUpClass(cls, chart_template_ref="bg"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.bg')
        cls.report = cls.env.ref('l10n_bg.l10n_bg_tax_report')

        cls.account_453100 = cls.env['account.account'].search([('code', '=like', '4531%')], limit=1)
        cls.account_453200 = cls.env['account.account'].search([('code', '=like', '4532%')], limit=1)
        cls.account_453800 = cls.env['account.account'].search([('code', '=like', '4538%')], limit=1)
        cls.account_453900 = cls.env['account.account'].search([('code', '=like', '4539%')], limit=1)
        cls.account_outstanding = cls.company_data['company'].account_journal_payment_debit_account_id

    def _create_invoice(self, invoice_type, amount, date, tax, journal):
        move = self.env['account.move'].create({
            'move_type': invoice_type,
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data[journal].id,
            'invoice_date': date,
            'date': date,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'name': 'product test 1',
                    'price_unit': amount,
                    'tax_ids': tax.ids,
                }),
            ],
        })

        move.action_post()

    def _vat_closing(self, options):
        with patch.object(self.registry['account.move'], '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['l10n_bg.tax.report.handler']._generate_tax_closing_entries(self.report, options)
            vat_closing_move.action_post()

    def _fill_tax_report_line_50(self, amount, date):
        tax_sale = self.env['account.tax'].search([('name', '=', '20%'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        # We multiply the amount by '5' because this line is for tax amounts and the tax is of 20%.
        self._create_invoice('out_invoice', amount * 5, date, tax_sale, 'default_journal_sale')

    def _fill_tax_report_line_60(self, amount, date):
        tax_purchase = self.env['account.tax'].search([('name', '=', '20% FTC'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        # We multiply the amount by '5' because this line is for tax amounts and the tax is of 20%.
        self._create_invoice('in_invoice', amount * 5, date, tax_purchase, 'default_journal_purchase')

    def _fill_tax_report_line_80(self, amount, date):
        self._fill_tax_report_line_external_value('l10n_bg.l10n_bg_tax_report_80_tag', amount, date)

    def _fill_tax_report_line_81(self, amount, date):
        self._fill_tax_report_line_external_value('l10n_bg.l10n_bg_tax_report_81_tag', amount, date)

    def _fill_tax_report_line_82(self, amount, date):
        self._fill_tax_report_line_external_value('l10n_bg.l10n_bg_tax_report_82_tag', amount, date)

    def _fill_tax_report_line_external_value(self, target, amount, date):
        self.env['account.report.external.value'].create({
            'company_id': self.company_data['company'].id,
            'target_report_expression_id': self.env.ref(target).id,
            'name': 'Manual value',
            'date': fields.Date.from_string(date),
            'value': amount,
        })

    def test_tax_report_simple_deduction(self):
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')

        # Month 1
        self._fill_tax_report_line_60(400, '2023-01-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     0.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                    400.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                0.0),
            ],
            options,
        )

        # Month 2
        options = self._generate_options(self.report, '2023-02-01', '2023-02-28')

        self._fill_tax_report_line_60(200, '2023-02-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     0.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                    200.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                0.0),
            ],
            options,
        )

        # Month 3
        options = self._generate_options(self.report, '2023-03-01', '2023-03-31')

        self._fill_tax_report_line_50(150, '2023-03-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                   Balance
            [   0,                                                                                                           1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      150.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 600 in refund, we deduct 150 from it. We are entitled to 450 now.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      150.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                   0.0),
            ],
            options,
        )

    def test_tax_report_partial_deduction(self):
        # Month 1
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')

        self._fill_tax_report_line_60(400, '2023-01-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     0.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                    400.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                0.0),
            ],
            options,
        )

        # Month 2
        options = self._generate_options(self.report, '2023-02-01', '2023-02-28')

        self._fill_tax_report_line_50(250, '2023-02-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      250.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 400 in refund, we deduct 250 from it. We are entitled to 150 now.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      250.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                   0.0),
            ],
            options,
        )

        # Month 3
        options = self._generate_options(self.report, '2023-03-01', '2023-03-31')

        self._fill_tax_report_line_50(250, '2023-03-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      250.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 150 in refund, we deduct 150 from it.
                # We are entitled to nothing more but still owe 100.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      150.0),
                # We pay the 100 that we still owe (after all deductions).
                ('[71] Tax for payment from Art. 50, effectively paid',                                                 100.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_does_not_change_simple_deduction(self):
        # Month 1
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')

        self._fill_tax_report_line_60(200, '2023-01-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     0.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                    200.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                0.0),
            ],
            options,
        )

        # Month 2
        options = self._generate_options(self.report, '2023-02-01', '2023-02-28')

        self._fill_tax_report_line_50(100, '2023-02-10')

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 200 in refund, we deduct 100 from it.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      100.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                   0.0),
            ],
            options,
        )

        self._vat_closing(options)

        # It should remain the same after the closing.
        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 200 in refund, we deduct 100 from it.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      100.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                   0.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_does_not_change_partial_deduction(self):
        # Month 1
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31')

        self._fill_tax_report_line_60(100, '2023-01-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     0.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                    100.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                ('[71] Tax for payment from Art. 50, effectively paid',                                                0.0),
            ],
            options,
        )

        # Month 2
        options = self._generate_options(self.report, '2023-02-01', '2023-02-28')

        self._fill_tax_report_line_50(200, '2023-02-10')

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      200.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 100 in refund, we deduct 100 from it.
                # We are entitled to nothing more but still owe 100.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      100.0),
                # We pay the 100 that we still owe (after all deductions).
                ('[71] Tax for payment from Art. 50, effectively paid',                                                 100.0),
            ],
            options,
        )

        self._vat_closing(options)

        # It should remain the same after the closing.
        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                  Balance
            [   0,                                                                                                          1],
            [
                ('Section C: Result for the period',                                                                       ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                      200.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                         0.0),

                ('Section D. VAT for deposition',                                                                          ''),
                # Since we are still entitled to 150 in refund, we deduct 150 from it.
                # We are entitled to nothing more but still owe 100.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      100.0),
                # We pay the 100 that we still owe (after all deductions).
                ('[71] Tax for payment from Art. 50, effectively paid',                                                 100.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_move_lines_on_exact_refundable_amount(self):
        # Month 1
        options = self._generate_options(self.report, '2023-04-01', '2023-04-30')

        self._fill_tax_report_line_60(100, '2023-04-10')
        self._vat_closing(options)

        # Month 2
        options = self._generate_options(self.report, '2023-05-01', '2023-05-31')

        self._fill_tax_report_line_80(100, '2023-05-10')

        with patch.object(self.registry['account.move'], '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['l10n_bg.tax.report.handler']._generate_tax_closing_entries(self.report, options).sorted('id')

            self.assertRecordValues(vat_closing_move.line_ids, [
                {'account_id': self.account_453200.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453100.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453800.id,      'debit':   0.0, 'credit': 100.0},
                {'account_id': self.account_outstanding.id, 'debit': 100.0, 'credit':   0.0},
            ])

            vat_closing_move.action_post()

        # Month 3
        options = self._generate_options(self.report, '2023-06-01', '2023-06-30')

        self._fill_tax_report_line_50(100, '2023-06-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                   100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                      0.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                # Since we asked for the correct vat refund amount, we are entitled to nothing more. We pay 100.
                ('[71] Tax for payment from Art. 50, effectively paid',                                              100.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_move_lines_on_insufficient_refundable_amount(self):
        # Month 1
        options = self._generate_options(self.report, '2023-04-01', '2023-04-30')

        self._fill_tax_report_line_60(100, '2023-04-10')
        self._vat_closing(options)

        # Month 2
        options = self._generate_options(self.report, '2023-05-01', '2023-05-31')

        self._fill_tax_report_line_80(50, '2023-05-10')

        with patch.object(self.registry['account.move'], '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['l10n_bg.tax.report.handler']._generate_tax_closing_entries(self.report, options).sorted('id')

            self.assertRecordValues(vat_closing_move.line_ids, [
                {'account_id': self.account_453200.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453100.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453800.id,      'debit':   0.0, 'credit':  50.0},
                {'account_id': self.account_outstanding.id, 'debit':  50.0, 'credit':   0.0},
            ])

            vat_closing_move.action_post()

        # Month 3
        options = self._generate_options(self.report, '2023-06-01', '2023-06-30')

        self._fill_tax_report_line_50(100, '2023-06-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                                 Balance
            [   0,                                                                                                         1],
            [
                ('Section C: Result for the period',                                                                      ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                     100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                        0.0),

                ('Section D. VAT for deposition',                                                                         ''),

                # Since we asked for the incorrect vat refund amount, we are still entitled to 50 in refund.
                # We deduct it here.
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',      50.0),
                # We pay the 50 that we still owe (after all deductions).
                ('[71] Tax for payment from Art. 50, effectively paid',                                                 50.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_move_lines_on_excessive_refundable_amount(self):
        # Month 1
        options = self._generate_options(self.report, '2023-04-01', '2023-04-30')

        self._fill_tax_report_line_60(100, '2023-04-10')
        self._vat_closing(options)

        # Month 2
        options = self._generate_options(self.report, '2023-05-01', '2023-05-31')

        self._fill_tax_report_line_80(150, '2023-05-10')

        with patch.object(self.registry['account.move'], '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['l10n_bg.tax.report.handler']._generate_tax_closing_entries(self.report, options).sorted('id')

            self.assertRecordValues(vat_closing_move.line_ids, [
                {'account_id': self.account_453200.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453100.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453800.id,      'debit':   0.0, 'credit': 150.0},
                {'account_id': self.account_outstanding.id, 'debit': 150.0, 'credit':   0.0},
            ])

            vat_closing_move.action_post()

        # Month 3
        options = self._generate_options(self.report, '2023-06-01', '2023-06-30')

        self._fill_tax_report_line_50(100, '2023-06-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                   100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                      0.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                # Although we asked for the incorrect vat refund amount, the error is not reflected on the report.
                # We pay 100.
                ('[71] Tax for payment from Art. 50, effectively paid',                                              100.0),
            ],
            options,
        )

    def test_tax_report_vat_closing_move_lines_on_premature_refund(self):
        # Month 1
        options = self._generate_options(self.report, '2023-04-01', '2023-04-30')

        self._fill_tax_report_line_80(100, '2023-04-10')

        with patch.object(self.registry['account.move'], '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = self.env['l10n_bg.tax.report.handler']._generate_tax_closing_entries(self.report, options).sorted('id')

            self.assertRecordValues(vat_closing_move.line_ids, [
                {'account_id': self.account_453200.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453100.id,      'debit':   0.0, 'credit':   0.0},
                {'account_id': self.account_453900.id,      'debit':   0.0, 'credit': 100.0},
                {'account_id': self.account_outstanding.id, 'debit': 100.0, 'credit':   0.0},
            ])

            vat_closing_move.action_post()

        # Month 2
        options = self._generate_options(self.report, '2023-05-01', '2023-05-31')

        self._fill_tax_report_line_50(100, '2023-05-10')
        self._vat_closing(options)

        self.assertLinesValues(
            self.report._get_lines(options)[30:36],
            #   Name                                                                                               Balance
            [   0,                                                                                                       1],
            [
                ('Section C: Result for the period',                                                                    ''),
                ('[50] VAT to be paid (class 20 - class 40) >= 0',                                                   100.0),
                ('[60] VAT for refund (class 20 - class 40) < 0',                                                      0.0),

                ('Section D. VAT for deposition',                                                                       ''),
                ('[70] Tax for payment from Art. 50, deducted in accordance with Art. 92, para. 1 of the VAT Act',     0.0),
                # Although we asked for the incorrect vat refund amount, the error is not reflected on the report.
                # We pay 100.
                ('[71] Tax for payment from Art. 50, effectively paid',                                              100.0),
            ],
            options,
        )
