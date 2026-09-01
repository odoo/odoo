from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTaxesTaxTotalsSummaryL10nAr(TestTaxesTaxTotalsSummary):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ar')
    def setUpClass(cls):
        super().setUpClass()

    def _test_taxes_l10n_ar(self):
        tax_21 = self.percent_tax(21, tax_group_id=self.tax_groups[0].id)
        tax_0_2 = self.percent_tax(0.2, tax_group_id=self.tax_groups[1].id)

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 7.0, 'price_unit': 124.0, 'tax_ids': tax_21 + tax_0_2},
            ],
            currency=self.foreign_currency,
            rate=1 / 1129.179,
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 868.0,
            'base_amount': 980127.37,
            'tax_amount_currency': 184.02,
            'tax_amount': 207791.52,
            'total_amount_currency': 1052.02,
            'total_amount': 1187918.89,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 868.0,
                    'base_amount': 980127.37,
                    'tax_amount_currency': 184.02,
                    'tax_amount': 207791.52,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 868.0,
                            'base_amount': 980127.37,
                            'tax_amount_currency': 182.28,
                            'tax_amount': 205826.75,
                            'display_base_amount_currency': 868.0,
                            'display_base_amount': 980127.37,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 868.0,
                            'base_amount': 980127.37,
                            'tax_amount_currency': 1.74,
                            'tax_amount': 1964.77,
                            'display_base_amount_currency': 868.0,
                            'display_base_amount': 980127.37,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

    def test_taxes_l10n_ar_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_ar():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_ar_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_ar():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)
