# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.sale.tests.common import SaleCommon


@tagged('-at_install', 'post_install')
class TestSaleReportCurrencyRate(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.usd_cmp = cls.env['res.company'].create({
            'name': 'USD Company', 'currency_id': cls.env.ref('base.USD').id,
        })
        cls.eur_cmp = cls.env['res.company'].create({
            'name': 'EUR Company', 'currency_id': cls.env.ref('base.EUR').id,
        })

    def test_sale_report_foreign_currency(self):
        """
        Test that amounts are correctly converted between currencies.
        There are two different conversions to take into account:
        - currency of the sale order pricelist -> currency of the sale order company
        - currency of sale order company -> currency of the current user company
        Adjustment between past and present rates must also be taken into account.
        """

        companies = self.usd_cmp + self.eur_cmp
        today = fields.Date.today()
        past_day = fields.Date.to_date('2020-01-01')
        usd = self.usd_cmp.currency_id
        eur = self.eur_cmp.currency_id
        ars = self._enable_currency('ARS')

        # Create corresponding pricelists and rates.
        pricelists = self.env['product.pricelist'].create([
            {'name': 'Pricelist (USD)', 'currency_id': usd.id, 'company_id': False},
            {'name': 'Pricelist (EUR)', 'currency_id': eur.id, 'company_id': False},
            {'name': 'Pricelist (ARS)', 'currency_id': ars.id, 'company_id': False},
        ])
        self.env['res.currency.rate'].create([
            {'name': past_day, 'rate': 555, 'currency_id': ars.id, 'company_id': self.eur_cmp.id},
            {'name': past_day, 'rate': 1.0, 'currency_id': eur.id, 'company_id': self.eur_cmp.id},
            {'name': past_day, 'rate': 999, 'currency_id': usd.id, 'company_id': self.eur_cmp.id},
            {'name': past_day, 'rate': 3.0, 'currency_id': ars.id, 'company_id': self.usd_cmp.id},
            {'name': past_day, 'rate': 0.1, 'currency_id': eur.id, 'company_id': self.usd_cmp.id},
            {'name': past_day, 'rate': 1.0, 'currency_id': usd.id, 'company_id': self.usd_cmp.id},
            {'name': today, 'rate': 222, 'currency_id': ars.id, 'company_id': self.eur_cmp.id},
            {'name': today, 'rate': 1.0, 'currency_id': eur.id, 'company_id': self.eur_cmp.id},
            {'name': today, 'rate': 2.9, 'currency_id': usd.id, 'company_id': self.eur_cmp.id},
            {'name': today, 'rate': 101, 'currency_id': ars.id, 'company_id': self.usd_cmp.id},
            {'name': today, 'rate': 0.6, 'currency_id': eur.id, 'company_id': self.usd_cmp.id},
            {'name': today, 'rate': 1.0, 'currency_id': usd.id, 'company_id': self.usd_cmp.id},
        ])

        self.assertEqual(self.product.currency_id, usd)

        # Needed to get conversion rates between companies.
        currency_rates = (companies + self.env.company).mapped('currency_id')._get_rates(
            self.env.company, today
        )

        sale_orders = self.env['sale.order']
        expected_reported_amount = 0  # The total amount of all sale orders in the report.
        qty = 0  # to add variety to the data

        # Create sale orders
        for company in companies:
            SaleOrder = self.env['sale.order'].with_company(company)
            for date in (past_day, today):
                for pricelist in pricelists:
                    qty += 1
                    order = SaleOrder.create({
                        'partner_id': self.partner.id,
                        'pricelist_id': pricelist.id,
                        'date_order': date,
                        'order_line': [Command.create(
                            {'product_id': self.product.id, 'product_uom_qty': qty}
                        )],
                    })
                    sale_orders |= order

                    expected_so_currency_rate = self.env['res.currency.rate'].search([
                        ('name', '=', date),
                        ('currency_id', '=', pricelist.currency_id.id),
                        ('company_id', '=', company.id),
                    ]).rate
                    expected_product_currency_rate = self.env['res.currency.rate'].search([
                        ('name', '=', date),
                        ('currency_id', '=', self.product.currency_id.id),
                        ('company_id', '=', company.id),
                    ]).rate

                    # To find the total amount we convert the price of the product from its currency
                    # to the currency of the so company and then from it to the currency of the so
                    # pricelist.
                    price_for_so_company = self.product.list_price / expected_product_currency_rate
                    expected_rounded_price = pricelist.currency_id.round(
                        price_for_so_company * expected_so_currency_rate
                    )

                    expected_amount_total = qty * expected_rounded_price
                    self.assertAlmostEqual(order.currency_rate, expected_so_currency_rate)
                    self.assertAlmostEqual(order.amount_total, expected_amount_total)

                    # The amount in the report is converted first to the currency of the company and
                    # then to the currency of the current company (self.env.company).
                    current_company_rate = currency_rates[self.env.company.currency_id.id]
                    so_company_rate = currency_rates[company.currency_id.id]
                    conversion_rate = (current_company_rate / so_company_rate)
                    expected_reported_amount += (
                        order.amount_total / order.currency_rate * conversion_rate
                    )

        # The report should show the amount in the current (in this case usd) company currency.
        report_lines = self.env['sale.report'].sudo().with_context(
            allow_company_ids=[self.usd_cmp.id, self.eur_cmp.id]
        ).search([('order_reference', 'in', [f'sale.order,{so_id}' for so_id in sale_orders.ids])])

        price_total = sum(report_lines.mapped('price_total'))
        self.assertAlmostEqual(price_total, expected_reported_amount)

    def test_sale_report_with_downpayment(self):
        """Checks that downpayment lines are used in the calculation of amounts invoiced and to invoice"""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
            })]
        })
        order.action_confirm()

        downpayment = self.env['sale.advance.payment.inv'].with_context(active_ids=order.ids).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 200
        })
        downpayment.create_invoices()
        order.invoice_ids.action_post()
        order.order_line.flush_recordset()

        amount_line = self.env['sale.report'].read_group(
            [('order_reference', '=', f'sale.order,{order.id}')],
            ['untaxed_amount_to_invoice:sum', 'untaxed_amount_invoiced:sum'],
            []
        )[0]

        self.assertEqual(float_compare(amount_line['untaxed_amount_invoiced'], 200, precision_rounding=order.currency_id.rounding), 0)
        self.assertEqual(float_compare(amount_line['untaxed_amount_to_invoice'], self.product.lst_price - 200, precision_rounding=order.currency_id.rounding), 0)
