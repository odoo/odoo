from odoo import Command
from odoo.tests.common import tagged
from odoo.addons.account.models.account_report import AGGREGATION_ENGINE_FORMULA_REGEX
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrTaxReport(AccountTestInvoicingCommon):

    def test_t_taxes_balance_check_no_warning(self):
        """
        Verify that the French tax report raises no warning when T1-T7 taxes are used.
        The report's check compares the sum of A-boxes against the sum of T-base boxes;
        both sides must balance for the warning to be absent.
        Each T-tax shares the `A1` base tag, which is what links them to the A-box totals.
        T7's percent (5.0) is arbitrary as it has no predefined value in the localization.
        """
        fr = self.env.ref('base.fr')
        a_base = self.env['account.account.tag']._get_tax_tags('A1', fr.id)

        def _create_t_tax(name, percent):
            tag_t_base = self.env['account.account.tag']._get_tax_tags(f'{name}_base', fr.id) | a_base
            tag_t_tax = self.env['account.account.tag']._get_tax_tags(f'{name}_taxe', fr.id)
            return self.percent_tax(
                percent,
                name=f'{name}_tax',
                invoice_repartition_line_ids=[
                    Command.create({'repartition_type': 'base', 'tag_ids': [Command.set(tag_t_base.ids)]}),
                    Command.create({'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id, 'tag_ids': [Command.set(tag_t_tax.ids)]}),
                ],
                refund_repartition_line_ids=[
                    Command.create({'repartition_type': 'base', 'tag_ids': [Command.set(tag_t_base.ids)]}),
                    Command.create({'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id, 'tag_ids': [Command.set(tag_t_tax.ids)]}),
                ],
            )

        t_taxes_data = [('T1', 1.75), ('T2', 1.05), ('T3', 10.0), ('T4', 2.1), ('T5', 0.9), ('T6', 2.1), ('T7', 5.0)]
        t_taxes = [_create_t_tax(tax_name, tax_percent) for tax_name, tax_percent in t_taxes_data]
        for tax in t_taxes:
            self._create_invoice(date="2019-01-01", invoice_line_ids=[self._prepare_invoice_line(price_unit=1000, tax_ids=tax)], post=True)

        report = self.env.ref('l10n_fr_account.tax_report').with_company(self.company_data['company'])
        options = report.get_options({
            'date': {
                'date_from': '2019-01-01',
                'date_to': '2019-01-31',
            }
        })
        report_information = report.get_report_information(options)
        self.assertNotIn('l10n_fr_reports.tax_report_warning_checks', report_information['warnings'])


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrTaxReportNegativeDeductibleVat(AccountTestInvoicingCommon):
    """Boxes 19 and 20 are clamped to zero for display and e-filing.

    When vendor refunds exceed vendor bills, the clamped excess must not vanish:
    it is reversed into box 15 (previously deducted VAT to be repaid), which
    feeds box 16 and therefore the VAT due line.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('l10n_fr_account.tax_report')
        cls.sale_tax_20 = cls.env['account.chart.template'].with_company(cls.env.company).ref('tva_normale')
        cls.purchase_tax_20 = cls.env['account.chart.template'].with_company(cls.env.company).ref('tva_acq_normale')

    @classmethod
    def _expr(cls, name):
        return cls.env.ref(f'l10n_fr_account.{name}')

    def _get_balances(self, date_from, date_to):
        """Return {line code: value of its 'balance' expression} for the given period.

        Skips the test when only the community modules are installed, as the
        report values can only be computed by the report engine.
        """
        report = self.report.with_company(self.env.company)
        if not hasattr(report, '_compute_expression_totals_for_single_column_group'):
            self.skipTest("Computing report values requires the accounting reports module.")
        options = report.get_options({'date': {'date_from': date_from, 'date_to': date_to, 'mode': 'range', 'filter': 'custom'}})
        expression_totals = report._compute_expression_totals_for_single_column_group(options)
        return {
            expression.report_line_id.code: totals.get('value')
            for expression, totals in expression_totals.items()
            if expression.label == 'balance' and expression.report_line_id.code
        }

    def test_clamped_deductible_boxes_keep_their_negative_excess(self):
        """The excess discarded by the zero clamp of boxes 19 and 20 is kept as a positive helper amount."""
        for box_code, spill_name, displayed_name in (
            ('box_19', 'tax_report_19_negative_spill', 'tax_report_19_tag'),
            ('box_20', 'tax_report_20_negative_spill', 'tax_report_20_tag'),
        ):
            with self.subTest(box=box_code):
                spill = self._expr(spill_name)
                self.assertEqual(spill.report_line_id.code, box_code)
                self.assertEqual(spill.label, 'negative_spill')
                self.assertEqual(spill.engine, 'aggregation')
                self.assertEqual(spill.formula, f'0 - {box_code}.balance_rounded')
                self.assertEqual(spill.subformula, f'if_other_expr_below({box_code}.balance_rounded, EUR(0))')
                self.assertTrue(AGGREGATION_ENGINE_FORMULA_REGEX.fullmatch(spill.formula))

                # The displayed amount still cannot go negative, so nothing negative is shown nor e-filed.
                displayed = self._expr(displayed_name)
                self.assertEqual(displayed.label, 'balance')
                self.assertEqual(displayed.formula, f'{box_code}.balance_rounded')
                self.assertEqual(displayed.subformula, f'if_other_expr_above({box_code}.balance_rounded, EUR(0))')

                # The helper is not bound to any column of the report, hence never rendered.
                self.assertNotIn('negative_spill', self.report.column_ids.mapped('expression_label'))

    def test_box_15_aggregates_the_clamped_deductible_excess(self):
        """Box 15 reclaims what boxes 19 and 20 dropped, and the amount reaches VAT due through box 16."""
        box_15_rounded = self._expr('tax_report_15_balance_rounded')
        self.assertEqual(box_15_rounded.formula, 'box_15.balance_from_tags + box_19.negative_spill + box_20.negative_spill')
        self.assertTrue(AGGREGATION_ENGINE_FORMULA_REGEX.fullmatch(box_15_rounded.formula))

        terms = box_15_rounded._get_aggregation_terms_details()
        self.assertEqual(terms['box_15'], {'balance_from_tags'})
        self.assertEqual(terms['box_19'], {'negative_spill'})
        self.assertEqual(terms['box_20'], {'negative_spill'})

        # Every referenced term resolves to an existing expression of the same report.
        dependencies = box_15_rounded._expand_aggregations()
        for expression_name in ('tax_report_15_balance_from_tags', 'tax_report_19_negative_spill', 'tax_report_20_negative_spill'):
            self.assertIn(self._expr(expression_name), dependencies)

        # No cycle: the helpers only depend on their own box, never back on box 15.
        for expression_name in ('tax_report_19_negative_spill', 'tax_report_20_negative_spill'):
            self.assertNotIn(box_15_rounded, self._expr(expression_name)._expand_aggregations())

        # Box 16 consumes box 15, and box 23 keeps summing the clamped deductible balances.
        self.assertIn('box_15.balance', self._expr('tax_report_16_formula').formula)
        self.assertIn('box_20.balance ', self._expr('tax_report_23_formula').formula)

    def test_vendor_refunds_exceeding_bills_are_reversed_into_box_15(self):
        """Net-negative deductible VAT increases VAT due instead of being silently dropped."""
        self._create_invoice(
            move_type='out_invoice', date='2019-01-10', post=True,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=500, tax_ids=self.sale_tax_20)],
        )
        self._create_invoice(
            move_type='in_invoice', date='2019-01-10', post=True,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=70, tax_ids=self.purchase_tax_20)],
        )
        self._create_invoice(
            move_type='in_refund', date='2019-01-20', post=True,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=140, tax_ids=self.purchase_tax_20)],
        )

        balances = self._get_balances('2019-01-01', '2019-01-31')
        # Deductible VAT nets to -14: box 20 stays blank, and the 14 is repaid through box 15.
        self.assertFalse(balances['box_20'])
        self.assertEqual(balances['box_15'], 14)
        self.assertEqual(balances['box_23'], 0)
        self.assertEqual(balances['box_16'], 114)
        self.assertEqual(balances['box_TD'], 114)

    def test_positive_deductible_vat_is_unaffected(self):
        """A normally deductible period keeps its deduction and triggers no reversal in box 15."""
        self._create_invoice(
            move_type='out_invoice', date='2019-01-10', post=True,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=500, tax_ids=self.sale_tax_20)],
        )
        self._create_invoice(
            move_type='in_invoice', date='2019-01-10', post=True,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=70, tax_ids=self.purchase_tax_20)],
        )

        balances = self._get_balances('2019-01-01', '2019-01-31')
        self.assertEqual(balances['box_20'], 14)
        self.assertFalse(balances['box_15'])
        self.assertEqual(balances['box_23'], 14)
        self.assertEqual(balances['box_16'], 100)
        self.assertEqual(balances['box_TD'], 86)
