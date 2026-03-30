# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged
from odoo.tools import float_round, float_compare

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon


@tagged('-at_install', 'post_install')
class TestProjectPurchaseProfitability(TestProjectProfitabilityCommon, TestPurchaseToInvoiceCommon):

    def test_bills_without_purchase_order_are_accounted_in_profitability(self):
        """
        A bill that has an AAL on one of its line should be taken into account
        for the profitability of the project.
        The contribution of the line should only be dependent
        on the project's analytic account % that was set on the line
        """
        # a custom analytic contribution (number between 1 -> 100 included)
        analytic_distribution = 42
        analytic_contribution = analytic_distribution / 100.
        price_precision = self.env['decimal.precision'].precision_get('Product Price')
        # create a bill_1 with the AAL
        bill_1 = self.env['account.move'].create({
            "name": "Bill_1 name",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })
        # the bill_1 is in draft, therefor it should have the cost "to_bill" same as the -product_price (untaxed)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price * analytic_contribution,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price * analytic_contribution, 'billed': 0.0},
            },
        )
        # post bill_1
        bill_1.action_post()
        # we posted the bill_1, therefore the cost "billed" should be -product_price, to_bill should be back to 0
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -self.product_a.standard_price * analytic_contribution,
                }],
                'total': {'to_bill': 0.0, 'billed': -self.product_a.standard_price * analytic_contribution},
            },
        )
        # create another bill, with 3 lines, 2 diff products, the second line has 2 as quantity, the third line has a negative price
        bill_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.env.company.currency_id.id,
            }), Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
                "currency_id": self.env.company.currency_id.id,
            }), Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.service_deliver.id,
                "quantity": 1,
                "product_uom_id": self.service_deliver.uom_id.id,
                "price_unit": -self.service_deliver.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })
        # bill_2 is not posted, therefor its cost should be "to_billed" = - sum of all product_price * qty for each line
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -(self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                    'billed': -self.product_a.standard_price * analytic_contribution,
                }],
                'total': {
                    'to_bill': -(self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                    'billed': -self.product_a.standard_price * analytic_contribution,
                },
            },
        )
        # post bill_2
        bill_2.action_post()
        # bill_2 is posted, therefor its cost should be counting in "billed", with the cost of bill_1
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                },
            },
        )
        # create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            "name": "A purchase order",
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.order_line.flush_recordset()
        # we should have a new section "purchase_order", the total should be updated,
        # but the "other_purchase_costs" shouldn't change, as we don't takes into
        # account bills from purchase orders, as those are already taken into calculations
        # from the purchase orders (in "purchase_order" section)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': 0.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': float_round(-(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution, precision_digits=price_precision),
                }],
                'total': {
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': float_round(-(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution, precision_digits=price_precision),
                },
            },
        )
        purchase_order.action_create_invoice()
        purchase_bill = purchase_order.invoice_ids  # get the bill from the purchase
        purchase_bill.invoice_date = datetime.today()
        purchase_bill.action_post()
        # now the bill has been posted, its costs should be accounted in the "billed" part
        # of the purchase_order section, but should touch in the other_purchase_costs
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': 0.0,
                    'billed': -self.product_order.standard_price * analytic_contribution,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': float_round(-(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution, precision_digits=price_precision),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': float_round(-(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price +
                                self.product_order.standard_price) * analytic_contribution, precision_digits=price_precision),
                },
            },
        )

    def test_account_analytic_distribution_ratio(self):
        """
        When adding multiple account analytics on a purchase line, and one of those
        is from a project (for ex: project created on confirmed SO),
        then in the profitability only the corresponding ratio of the analytic distribution
        for that project analytic account should be taken into account.
        (for ex: if there are 2 accounts on 1 line, one is 60% project analytic account, 40% some other,
        then the profitability should only reflect 60% of the cost of the line, not 100%)
        """
        # define the ratios for the analytic account of the line
        analytic_ratios = {
            "project_ratio": 60,
            "other_ratio": 40,
        }
        self.assertEqual(sum(ratio for ratio in analytic_ratios.values()), 100)
        # create another analytic_account that is not really relevant
        other_analytic_account = self.env['account.analytic.account'].create({
            'name': 'Not important',
            'code': 'KO-1234',
            'plan_id': self.analytic_plan.id,
        })
        # create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            "name": "A purchase order",
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "analytic_distribution": {
                    # this is the analytic_account that is linked to the project
                    self.analytic_account.id: analytic_ratios["project_ratio"],
                    other_analytic_account.id: analytic_ratios["other_ratio"],
                },
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.order_line.flush_recordset()
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -(self.product_order.standard_price * (analytic_ratios["project_ratio"] / 100)),
                    'billed': 0.0,
                }],
                'total': {
                    'to_bill': -(self.product_order.standard_price * (analytic_ratios["project_ratio"] / 100)),
                    'billed': 0.0,
                },
            },
        )
        purchase_order.action_create_invoice()
        purchase_bill = purchase_order.invoice_ids  # get the bill from the purchase
        purchase_bill.invoice_date = datetime.today()
        purchase_bill.action_post()
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': 0.0,
                    'billed': -(self.product_order.standard_price * (analytic_ratios["project_ratio"] / 100)),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -(self.product_order.standard_price * (analytic_ratios["project_ratio"] / 100)),
                },
            },
        )

    def test_analytic_distribution_with_included_tax(self):
        """When calculating the profitability of a project, included taxes should not be calculated"""
        included_tax = self.env['account.tax'].create({
            'name': 'included tax',
            'amount': '15.0',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True
        })

        # create a purchase.order with the project account in analytic_distribution
        purchase_order = self.env['purchase.order'].create({
            'name': "A purchase order",
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'analytic_distribution': {self.analytic_account.id: 100},
                'product_id': self.product_order.id,
                'product_qty': 2,  # plural value to check if the price is multiplied more than once
                'taxes_id': [included_tax.id],  # set the included tax
                'price_unit': self.product_order.standard_price,
                'currency_id': self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.order_line.flush_recordset()
        # the profitability should not take taxes into account
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -(purchase_order.amount_untaxed),
                    'billed': 0.0,
                }],
                'total': {
                    'to_bill': -(purchase_order.amount_untaxed),
                    'billed': 0.0,
                },
            },
        )

        purchase_order.action_create_invoice()
        purchase_bill = purchase_order.invoice_ids  # get the bill from the purchase
        purchase_bill.invoice_date = datetime.today()
        purchase_bill.action_post()
        # same here, taxes should not be calculated in the profitability
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': 0.0,
                    'billed': -(purchase_bill.amount_untaxed),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -(purchase_bill.amount_untaxed),
                },
            },
        )

    def test_analytic_distribution_with_mismatched_uom(self):
        """When changing the unit of measure, the profitability should still match the price_subtotal of the order line"""
        # create a purchase.order with the project account in analytic_distribution
        purchase_order = self.env['purchase.order'].create({
            'name': "A purchase order",
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'analytic_distribution': {self.analytic_account.id: 100},
                'product_id': self.product_order.id,
                'product_qty': 1,
                'price_unit': self.product_order.standard_price,
                'currency_id': self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        # changing the uom to a higher number
        purchase_order.order_line.product_uom = self.env.ref("uom.product_uom_dozen")
        purchase_order.order_line.flush_recordset()
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -(purchase_order.amount_untaxed),
                    'billed': 0.0,
                }],
                'total': {
                    'to_bill': -(purchase_order.amount_untaxed),
                    'billed': 0.0,
                },
            },
        )

    def test_profitability_foreign_currency_rate_on_bill_date(self):
        """Test that project profitability uses the correct currency rate (on bill date) for vendor bills in foreign currency."""
        CurrencyRate = self.env['res.currency.rate']
        company = self.env.company

        # Pick a foreign currency different from company currency
        foreign_currency = self.env['res.currency'].search([('id', '!=', company.currency_id.id)], limit=1)
        if not foreign_currency:
            foreign_currency = self.env['res.currency'].create({'name': 'USD', 'symbol': '$', 'rounding': 0.01, 'decimal_places': 2})

        # Set two rates: yesterday and today
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        rate_today = 1.9
        rate_yesterday = 2.0
        CurrencyRate.create({
            'currency_id': foreign_currency.id,
            'rate': rate_yesterday,
            'name': yesterday,
            'company_id': company.id,
        })
        CurrencyRate.create({
            'currency_id': foreign_currency.id,
            'rate': rate_today,
            'name': today,
            'company_id': company.id,
        })

        # Create a vendor bill in foreign currency, dated yesterday, with analytic distribution to the project
        price_unit = 150
        bill = self.env['account.move'].create({
            "name": "Bill Foreign Currency",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": yesterday,
            "currency_id": foreign_currency.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": price_unit,
            })],
        })

        # Compute expected value: balance is in company currency, so should be price_unit / rate_yesterday (since bill is in foreign currency)
        expected_cost = -(price_unit / rate_yesterday)

        # Check profitability before posting (should be in 'to_bill')
        costs = self.project._get_profitability_items(False)['costs']
        self.assertEqual(len(costs['data']), 1)
        actual_to_bill = costs['data'][0]['to_bill']
        self.assertTrue(
            float_compare(actual_to_bill, expected_cost, precision_digits=2) == 0,
            f"Expected to_bill {expected_cost}, got {actual_to_bill}"
        )

        # Post the bill and check 'billed'
        bill.action_post()
        costs = self.project._get_profitability_items(False)['costs']
        actual_billed = costs['data'][0]['billed']
        self.assertTrue(
            float_compare(actual_billed, expected_cost, precision_digits=2) == 0,
            f"Expected billed {expected_cost}, got {actual_billed}"
        )
