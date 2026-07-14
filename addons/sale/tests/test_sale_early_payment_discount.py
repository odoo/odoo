# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.fields import Command

from odoo.addons.sale.tests.common import TestTaxCommonSale


@tagged('post_install', '-at_install')
class TestSaleEarlyPaymentDiscount(TestTaxCommonSale):

    def test_apply_mixed_epd_discount(self):
        """
        When applying an epd - mixed payment term, the tax should be computed based on the discounted untaxed amount.
        """
        tax_a = self.percent_tax(15.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set(tax_a.ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 13.5,
                'total_amount_currency': 113.5,
            },
            soft_checking=True,
        )

    def test_apply_mixed_epd_discount_fixed_tax(self):
        """
        When applying an epd - mixed payment term, the fixed tax amount should be the same.
        """
        tax_a = self.fixed_tax(20.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set(tax_a.ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 20.0,
                'total_amount_currency': 120.0,
            },
            soft_checking=True,
        )

    def test_apply_mixed_epd_discount_percent_and_fixed_tax(self):
        """
        When applying an epd - mixed payment term, the percent tax should be computed based on the discounted untaxed amount.
        """
        tax_a = self.percent_tax(15.0)
        tax_b = self.fixed_tax(20.0)
        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 20,
                }),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'payment_term_id': early_payment_term.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'tax_id': [Command.set((tax_a + tax_b).ids)],
                }),
            ],
        })
        self.assert_sale_order_tax_totals_summary(
            sale_order,
            {
                'base_amount_currency': 100.0,
                'tax_amount_currency': 33.5,
                'total_amount_currency': 133.5,
            },
            soft_checking=True,
        )

    def test_early_payment_discount(self):
        """Ensure untaxed amount in sale order is correct when early payment discount
        is applied on tax-included price.
        """
        tax = self.percent_tax(21, price_include_override='tax_included')
        product = self._create_product(lst_price=7.5, taxes_id=tax)
        self.pay_terms_a.early_discount = True
        self.pay_terms_a.early_pay_discount_computation = "mixed"
        sale_order = self._create_sale_order_one_line(product_id=product, payment_term_id=self.pay_terms_a)
        self.assertRecordValues(sale_order, [{
            'amount_untaxed': 6.2,
            'amount_tax': 1.27,
            'amount_total': 7.47,
        }])
