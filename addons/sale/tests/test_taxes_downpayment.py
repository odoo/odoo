from odoo.addons.account.tests.test_taxes_downpayment import TestTaxesDownPayment
from odoo.addons.sale.tests.common import TestTaxCommonSale
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesDownPaymentSale(TestTaxCommonSale, TestTaxesDownPayment):

    def assert_sale_order_down_payment(
        self,
        sale_order,
        amount_type,
        amount,
        expected_values,
        soft_checking=False,
    ):
        """ Assert the expected values for the tax totals summary of the
        down payment invoice generated from the sale order passed as parameter.
        Then, generate the final invoice and assert its total is well the original
        total amount of the sale order minus the previously generated down payment.

        :param sale_order:      The SO as a sale.order record.
        :param amount_type:     The type of the global discount: 'percent' or 'fixed'.
        :param amount:          The amount to consider.
                                For 'percent', it should be a percentage [0-100].
                                For 'fixed', any amount.
        :param expected_values: The expected values for the tax_total_summary.
        :param soft_checking:   Limit the asserted values to the ones in 'expected_results'
                                and don't go deeper inside the tax_total_summary.
                                It allows to assert only the totals without asserting all the
                                tax details.
        """
        if amount_type == 'percent':
            advance_payment_method = 'percentage'
            percent_amount = amount
            fixed_amount = None
        else:  # amount_type == 'fixed'
            advance_payment_method = 'fixed'
            percent_amount = None
            fixed_amount = amount

        original_amount_total = sale_order.amount_total
        downpayment_wizard = self.env['sale.advance.payment.inv']\
            .with_context({'active_model': sale_order._name, 'active_ids': sale_order.ids})\
            .create({
                'advance_payment_method': advance_payment_method,
                'amount': percent_amount,
                'fixed_amount': fixed_amount,
            })
        action_values = downpayment_wizard.create_invoices()
        invoice = self.env['account.move'].browse(action_values['res_id'])
        self._assert_tax_totals_summary(
            invoice.tax_totals,
            expected_values,
            soft_checking=soft_checking,
        )

        # Full invoice.
        downpayment_wizard = self.env['sale.advance.payment.inv']\
            .with_context({'active_model': sale_order._name, 'active_ids': sale_order.ids})\
            .create({
                'advance_payment_method': 'delivered',
                'amount': percent_amount,
                'fixed_amount': fixed_amount,
            })
        action_values = downpayment_wizard.create_invoices()
        invoice = self.env['account.move'].browse(action_values['res_id'])
        self.assertRecordValues(invoice, [
            {'amount_total': original_amount_total - expected_values['total_amount_currency']},
        ])

    def test_taxes_l10n_in_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_br_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_be_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_fixed_tax_last_position_sale_orders(self):
        for test_mode, document, amount_type, amount, expected_values in self._test_taxes_fixed_tax_last_position():
            with self.subTest(test_code=test_mode):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values)

    def test_no_taxes_sale_orders(self):
        document, amount_type, amount, expected_values = self._test_no_taxes()
        sale_order = self.convert_document_to_sale_order(document)
        sale_order.action_confirm()
        self.assert_sale_order_down_payment(sale_order, amount_type, amount, expected_values)
