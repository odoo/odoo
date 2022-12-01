# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon


@tagged('-at_install', 'post_install')
class TestProjectPurchaseProfitability(TestProjectProfitabilityCommon, TestPurchaseToInvoiceCommon):

    def test_bills_without_purchase_order_are_accounted_in_profitability(self):
        """
        A bill that has an AAL on one of its line should be taken into account
        for the profitability of the project.
        """
        # create a bill_1 with the AAL
        bill_1 = self.env['account.move'].create({
            "name": "Bill_1 name",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_account_id": self.analytic_account.id,
                "product_id": self.product_a,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            })],
        })
        # the bill_1 is in draft, therefor it should have the cost "to_bill" same as the -product_price (untaxed)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price, 'billed': 0.0},
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
                    'billed': -self.product_a.standard_price,
                }],
                'total': {'to_bill': 0.0, 'billed': -self.product_a.standard_price},
            },
        )
        # create another bill, with 2 lines, 2 diff products, the second line has 2 as quantity
        bill_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_account_id": self.analytic_account.id,
                "product_id": self.product_a,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            }), Command.create({
                "analytic_account_id": self.analytic_account.id,
                "product_id": self.product_b,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
            })],
        })
        # bill_2 is not posted, therefor its cost should be "to_billed" = - sum of all product_price * qty for each line
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price,
                }],
                'total': {
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price,
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
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
                },
            },
        )
        # create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            "name": "A purchase order",
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "account_analytic_id": self.analytic_account.id,
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
            })],
        })
        purchase_order.button_confirm()
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
                    'to_bill': -self.product_order.standard_price,
                    'billed': 0.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': -self.product_order.standard_price,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
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
                    'billed': -self.product_order.standard_price,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price +
                                self.product_order.standard_price),
                },
            },
        )
