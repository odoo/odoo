from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPtTaxTotalsSummary(TestTaxesTaxTotalsSummary):
    def _jsonify_document_line(self, document, index, line):
        # EXTENDS 'account'.
        values = super()._jsonify_document_line(document, index, line)
        if l10n_pt_line_discount := line.get('l10n_pt_line_discount'):
            values['l10n_pt_line_discount'] = l10n_pt_line_discount
        return values

    def convert_base_line_to_invoice_line(self, document, base_line):
        # EXTENDS 'account'.
        values = super().convert_base_line_to_invoice_line(document, base_line)
        if l10n_pt_line_discount := base_line.get('l10n_pt_line_discount'):
            values['l10n_pt_line_discount'] = l10n_pt_line_discount
        return values

    def convert_document_to_invoice(self, document):
        invoice = super().convert_document_to_invoice(document)
        if global_discount := document.get('l10n_pt_global_discount'):
            invoice.l10n_pt_global_discount = global_discount
        return invoice

    def populate_document(self, document):
        if document.get('l10n_pt_line_discount') or document.get('line_discount'):
            document = self._l10n_pt_add_discount(document)
        return super().populate_document(document)

    # -------------------------------------------------------------------------
    # Compute discount
    # -------------------------------------------------------------------------

    def _l10n_pt_add_discount(self, document):
        """
        Simulate behavior of _compute_discount in l10n_pt, which sets the discount amount
        based on l10n_pt_line_discount and l10n_pt_global_discount.
        """
        global_discount = document.get('l10n_pt_global_discount', 0.0) / 100
        for line in document['lines']:
            line_discount = line.get('l10n_pt_line_discount', 0.0) / 100
            line['discount'] = (1 - (1 - global_discount) * (1 - line_discount)) * 100
        return document

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_taxes_l10n_pt_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                if document.get('l10n_pt_line_discount') or document.get('line_discount'):
                    document = self._l10n_pt_add_discount(document)
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_pt_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_taxes_l10n_pt(self):
        """ !!!! THOSE TESTS ARE THERE TO CERTIFY THE USE OF ODOO INVOICING IN PORTUGAL.
        Therefore, they have to stay like this to stay compliant.
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        self.change_company_country(self.env.company, self.env.ref('base.pt'))
        self.env['decimal.precision'].search([('name', '=', "Product Price")]).digits = 6
        tax_0 = self.percent_tax(0, tax_group_id=self.tax_groups[0].id)
        tax_6 = self.percent_tax(6, tax_group_id=self.tax_groups[1].id)
        tax_13 = self.percent_tax(13, tax_group_id=self.tax_groups[2].id)
        tax_23 = self.percent_tax(23, tax_group_id=self.tax_groups[3].id)

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.79,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 293.79,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.79,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 293.79,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.79,
            'tax_amount_currency': 38.19,
            'total_amount_currency': 331.98,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.79,
                    'tax_amount_currency': 38.19,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 38.19,
                            'display_base_amount_currency': 293.79,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.78,
            'tax_amount_currency': 52.89,
            'total_amount_currency': 346.67,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.78,
                    'tax_amount_currency': 52.89,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 19.1,
                            'display_base_amount_currency': 146.89,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 33.79,
                            'display_base_amount_currency': 146.89,
                        },
                    ],
                },
            ],
        }
        yield 3, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 1.0, 'price_unit': 0.5, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 147.40,
            'tax_amount_currency': 33.9,
            'total_amount_currency': 181.30,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 147.40,
                    'tax_amount_currency': 33.9,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 147.40,
                            'tax_amount_currency': 33.9,
                            'display_base_amount_currency': 147.40,
                        },
                    ],
                },
            ],
        }
        yield 4, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_6},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_6},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 1175.16,
            'tax_amount_currency': 123.39,
            'total_amount_currency': 1298.55,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1175.16,
                    'tax_amount_currency': 123.39,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 17.63,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 38.19,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 67.57,
                            'display_base_amount_currency': 293.79,
                        },
                    ],
                },
            ],
        }
        yield 5, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
                {'quantity': 1, 'price_unit': 0.5, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 294.29,
            'tax_amount_currency': 67.69,
            'total_amount_currency': 361.98,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 294.29,
                    'tax_amount_currency': 67.69,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 294.29,
                            'tax_amount_currency': 67.69,
                            'display_base_amount_currency': 294.29,
                        },
                    ],
                },
            ],
        }
        yield 6, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_6},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 881.37,
            'tax_amount_currency': 114.57,
            'total_amount_currency': 995.94,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 881.37,
                    'tax_amount_currency': 114.57,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 146.89,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 146.90,
                            'tax_amount_currency': 8.81,
                            'display_base_amount_currency': 146.90,
                        },
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 38.19,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 67.57,
                            'display_base_amount_currency': 293.79,
                        },
                    ],
                },
            ],
        }
        yield 7, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 5.55, 'price_unit': 1.09, 'tax_ids': tax_23},
                {'quantity': 5.5, 'price_unit': 1.09, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 12.04,
            'tax_amount_currency': 2.77,
            'total_amount_currency': 14.81,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 12.04,
                    'tax_amount_currency': 2.77,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 12.04,
                            'tax_amount_currency': 2.77,
                            'display_base_amount_currency': 12.04,
                        },
                    ],
                },
            ],
        }
        yield 8, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_0},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_6},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_6},
                {'quantity': 13.13, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 13.13, 'price_unit': 12.12, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 1199.64,
            'tax_amount_currency': 127.80,
            'total_amount_currency': 1327.44,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1199.64,
                    'tax_amount_currency': 127.80,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 17.63,
                            'display_base_amount_currency': 293.79,
                        },
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 306.03,
                            'tax_amount_currency': 39.78,
                            'display_base_amount_currency': 306.03,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 306.03,
                            'tax_amount_currency': 70.39,
                            'display_base_amount_currency': 306.03,
                        },
                    ],
                },
            ],
        }
        yield 9, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 501.0, 'price_unit': 3.0, 'tax_ids': tax_6},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 1503.0,
            'tax_amount_currency': 90.18,
            'total_amount_currency': 1593.18,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1503.0,
                    'tax_amount_currency': 90.18,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 1503.0,
                            'tax_amount_currency': 90.18,
                            'display_base_amount_currency': 1503.0,
                        },
                    ],
                },
            ],
        }
        yield 10, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 146.89,
            'tax_amount_currency': 33.79,
            'total_amount_currency': 180.68,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 146.89,
                    'tax_amount_currency': 33.79,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 33.79,
                            'display_base_amount_currency': 146.89,
                        },
                    ],
                },
            ],
        }
        yield 11, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 50.0, 'price_unit': 2.0, 'tax_ids': tax_13},
                {'quantity': 100.0, 'price_unit': 1.0, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 200.0,
            'tax_amount_currency': 36.0,
            'total_amount_currency': 236.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 200.0,
                    'tax_amount_currency': 36.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 13.0,
                            'display_base_amount_currency': 100.0,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 23.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        yield 12, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 1.0, 'price_unit': 1.0, 'tax_ids': tax_0},
                {'quantity': 1.0, 'price_unit': 4.0, 'tax_ids': tax_0},
                {'quantity': 10.0, 'price_unit': 3.0, 'tax_ids': tax_6},
                {'quantity': 1.0, 'price_unit': 2.0, 'tax_ids': tax_13},
                {'quantity': 1.0, 'price_unit': 1.0, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 38.0,
            'tax_amount_currency': 2.29,
            'total_amount_currency': 40.29,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 38.0,
                    'tax_amount_currency': 2.29,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 5.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 5.0,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 30.0,
                            'tax_amount_currency': 1.8,
                            'display_base_amount_currency': 30.0,
                        },
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 2.0,
                            'tax_amount_currency': 0.26,
                            'display_base_amount_currency': 2.0,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 1.0,
                            'tax_amount_currency': 0.23,
                            'display_base_amount_currency': 1.0,
                        },
                    ],
                },
            ],
        }
        yield 13, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 50.0, 'price_unit': 1.09, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 54.5,
            'tax_amount_currency': 12.54,
            'total_amount_currency': 67.04,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 54.5,
                    'tax_amount_currency': 12.54,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 54.5,
                            'tax_amount_currency': 12.54,
                            'display_base_amount_currency': 54.5,
                        },
                    ],
                },
            ],
        }
        yield 14, document, expected_values

        document_vals = self.init_document(
            lines=[
                {'quantity': 100.0, 'price_unit': 0.55, 'l10n_pt_line_discount': 8.8, 'tax_ids': tax_23},
                {'quantity': 10.0, 'price_unit': 2.0, 'tax_ids': tax_23},
            ],
        )
        document_vals['line_discount'] = True
        document_vals['l10n_pt_global_discount'] = 10.0
        document = self.populate_document(document_vals)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 63.15,
            'tax_amount_currency': 14.52,
            'total_amount_currency': 77.67,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 63.15,
                    'tax_amount_currency': 14.52,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 63.15,
                            'tax_amount_currency': 14.52,
                            'display_base_amount_currency': 63.15,
                        },
                    ],
                },
            ],
        }
        yield 15, document, expected_values

        document_vals = self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'l10n_pt_line_discount': 6.6, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'l10n_pt_line_discount': 6.6, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'l10n_pt_line_discount': 8.8, 'tax_ids': tax_23},
                {'quantity': 12.12, 'price_unit': 12.12, 'l10n_pt_line_discount': 8.8, 'tax_ids': tax_23},
            ],
        )
        document_vals['line_discount'] = True
        document = self.populate_document(document_vals)
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 542.33,
            'tax_amount_currency': 97.30,
            'total_amount_currency': 639.63,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 542.33,
                    'tax_amount_currency': 97.30,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 274.4,
                            'tax_amount_currency': 35.67,
                            'display_base_amount_currency': 274.4,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 267.93,
                            'tax_amount_currency': 61.63,
                            'display_base_amount_currency': 267.93,
                        },
                    ],
                },
            ],
        }
        yield 16, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 13.13, 'price_unit': 13.13, 'tax_ids': tax_13},
                {'quantity': 1.0, 'price_unit': 0.5, 'tax_ids': tax_13},
                {'quantity': 1.0, 'price_unit': 0.5, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 173.39,
            'tax_amount_currency': 22.6,
            'total_amount_currency': 195.99,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 173.39,
                    'tax_amount_currency': 22.6,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 172.89,
                            'tax_amount_currency': 22.48,
                            'display_base_amount_currency': 172.89,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 0.5,
                            'tax_amount_currency': 0.12,
                            'display_base_amount_currency': 0.5,
                        },
                    ],
                },
            ],
        }
        yield 17, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 1.0, 'price_unit': 0.5, 'tax_ids': tax_13},
                {'quantity': 1.0, 'price_unit': 0.5, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 0.99,
            'tax_amount_currency': 0.19,
            'total_amount_currency': 1.18,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 0.99,
                    'tax_amount_currency': 0.19,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 0.5,
                            'tax_amount_currency': 0.07,
                            'display_base_amount_currency': 0.5,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 0.5,
                            'tax_amount_currency': 0.12,
                            'display_base_amount_currency': 0.5,
                        },
                    ],
                },
            ],
        }
        yield 18, document, expected_values
