from odoo.addons.account.tests.test_taxes_global_discount import TestTaxesGlobalDiscount
from odoo.addons.sale.tests.common import TestTaxCommonSale
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesGlobalDiscountSale(TestTaxCommonSale, TestTaxesGlobalDiscount):

    def assert_sale_order_global_discount(
        self,
        sale_order,
        amount_type,
        amount,
        expected_values,
        soft_checking=False,
    ):
        if amount_type == 'percent':
            discount_type = 'so_discount'
            discount_percentage = amount / 100.0
            discount_amount = None
        else:  # amount_type == 'fixed'
            discount_type = 'amount'
            discount_percentage = None
            discount_amount = amount
        discount_wizard = self.env['sale.order.discount']\
            .with_context({'active_model': sale_order._name, 'active_id': sale_order.id})\
            .create({
                'discount_type': discount_type,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
            })
        discount_wizard.action_apply_discount()
        self._assert_tax_totals_summary(
            sale_order.tax_totals,
            expected_values,
            soft_checking=soft_checking,
        )

    def test_taxes_l10n_in_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_global_discount(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_br_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_global_discount(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)

    def test_taxes_l10n_be_sale_orders(self):
        for test_mode, document, soft_checking, amount_type, amount, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_code=test_mode, amount=amount):
                sale_order = self.convert_document_to_sale_order(document)
                sale_order.action_confirm()
                self.assert_sale_order_global_discount(sale_order, amount_type, amount, expected_values, soft_checking=soft_checking)
