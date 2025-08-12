# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged
from odoo.tools import float_round

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('-at_install', 'post_install')
class TestProjectPurchaseProfitability(TestProjectProfitabilityCommon, TestPurchaseToInvoiceCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('purchase.group_purchase_user')
        cls.company_data_2 = cls.setup_other_company()

    def _create_invoice_for_po(self, purchase_order):
        purchase_order.action_create_invoice()
        purchase_bill = purchase_order.invoice_ids  # get the bill from the purchase
        purchase_bill.invoice_date = datetime.today()
        purchase_bill.action_post()
        return purchase_bill

    def test_bills_without_purchase_order_are_accounted_in_profitability_project_purchase(self):
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
        # add 2 new AAL to the analytic account. Those costs must be present in the cost data
        self.env['account.analytic.line'].create([{
            'name': 'extra costs 1',
            'account_id': self.analytic_account.id,
            'amount': -50.1,
        }, {
            'name': 'extra costs 2',
            'account_id': self.analytic_account.id,
            'amount': -100,
        }])
        # the bill_1 is in draft, therefore it should have the cost "to_bill" same as the -product_price (untaxed)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price * analytic_contribution,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price * analytic_contribution, 'billed': -150.1},
            },
        )
        # post bill_1
        bill_1.action_post()
        # we posted the bill_1, therefore the cost "billed" should be -product_price, to_bill should be back to 0
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -self.product_a.standard_price * analytic_contribution,
                }],
                'total': {'to_bill': 0.0, 'billed': -self.product_a.standard_price * analytic_contribution - 150.1},
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
        # bill_2 is not posted, therefore its cost should be "to_billed" = - sum of all product_price * qty for each line
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
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
                    'billed': -self.product_a.standard_price * analytic_contribution - 150.1,
                },
            },
        )
        # post bill_2
        bill_2.action_post()
        # bill_2 is posted, therefore its cost should be counting in "billed", with the cost of bill_1
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
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
                                self.service_deliver.standard_price) * analytic_contribution - 150.1,
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
        self.assertEqual(purchase_order.invoice_status, 'to invoice')
        # The section "purchase_order" should appear as the purchase order is validated, the total should be updated,
        # the "other_purchase_costs" shouldn't change, as we don't take into
        # account bills from purchase orders, as those are already taken into calculations
        # from the purchase orders (in "purchase_order" section)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                },{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': 0.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                }],
                'total': {
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution - 150.1,
                },
            },
        )
        # Create a vendor bill linked to the PO
        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_ids.state, 'draft')
        # now the bill has been created and set to draft so the section "purchase_order" should appear, its costs should be accounted in the "to bill" part
        # of the purchase_order section, but should touch in the other_purchase_costs
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': 0.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution,
                }],
                'total': {
                    'to_bill': -self.product_order.standard_price * analytic_contribution,
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price) * analytic_contribution -150.1,
                },
            },
        )
        # Post the vendor bill linked to the PO
        purchase_bill = purchase_order.invoice_ids
        purchase_bill.invoice_date = datetime.today()
        purchase_bill.action_post()
        self.assertEqual(purchase_order.invoice_ids.state, 'posted')
        # now the bill has been posted so the costs of the section "purchase_order" should be accounted in the "billed" part
        # and the total should be updated accordingly
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.1,
                }, {
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
                    'billed': -(2 * self.product_a.standard_price +
                                2 * self.product_b.standard_price -
                                self.service_deliver.standard_price +
                                self.product_order.standard_price) * analytic_contribution - 150.1,
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
        self.assertEqual(purchase_order.invoice_status, 'to invoice')
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
            'No data should be found since the purchase order is not invoiced.',
        )

        # Invoice the purchase order
        self._create_invoice_for_po(purchase_order)
        self.assertEqual(purchase_order.invoice_status, 'invoiced')
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

    def test_multi_currency_for_project_purchase_profitability(self):
        """ This test ensures that when purchase orders with different currencies are linked to the same project, the amount are correctly computed according to the
        rate of the company """
        project = self.env['project.project'].create({'name': 'new project'})
        project._create_analytic_account()
        account = project.account_id
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency

        # a custom analytic contribution (number between 1 -> 100 included)
        analytic_distribution = 42
        analytic_contribution = analytic_distribution / 100.
        # Create a bill_1 with the foreign_currency.
        bill_1 = self.env['account.move'].create({
            "name": "Bill foreign currency",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "date": datetime.today(),
            "invoice_date_due": datetime.today() - timedelta(days=1),
            "company_id": foreign_company.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id,
            }), Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 2,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
        })
        # Ensures that if no items have the main currency, the total is still displayed in the main currency.
        # Expected total : product_price * 0.2 (rate) * 3 (number of products).
        # Note : for some reason, the method to round the amount to the rounding of the currency is not 100% reliable.
        # We use a float_compare in order to ensure the value is close enough to the expected result. This problem has no repercusion on the client side, since
        # there is also a rounding method on this side to ensure the amount is correctly displayed.
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('other_purchase_costs', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][0]['sequence'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 0.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual(0.0, items['data'][0]['billed'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 0.6, items['total']['to_bill'], 2), 0)
        self.assertEqual(0.0, items['total']['billed'])

        # Create a bill 2 with the main currency.
        bill_2 = self.env['account.move'].create({
            "name": "Bill main currency",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.env.company.currency_id.id,
            }), Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 2,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })

        # The 2 bills are in draft, therefore the "to_bill" section should contain the total cost of the 2 bills.
        # The expected total is therefore product_price * 1 * 3 + product_price * 0.2 * 3 => * 3.6
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('other_purchase_costs', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][0]['sequence'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual(0.0, items['data'][0]['billed'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['total']['to_bill'], 2), 0)
        self.assertEqual(0.0, items['total']['billed'])

        # Bill 2 is posted. Its total is now in the 'billed' section, while the bill_1 is still in the 'to bill' one.
        bill_2.action_post()
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('other_purchase_costs', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][0]['sequence'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 0.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3, items['data'][0]['billed'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 0.6, items['total']['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3, items['total']['billed'], 2), 0)

        # Bill 1 is posted. Its total is now in the 'billed' section, the 'to bill' one should now be empty.
        bill_1.action_post()
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('other_purchase_costs', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][0]['sequence'])
        self.assertEqual(0.0, items['data'][0]['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][0]['billed'], 2), 0)
        self.assertEqual(0.0, items['total']['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['total']['billed'], 2), 0)

        # create a new purchase order with the foreign company
        purchase_order_foreign = self.env['purchase.order'].create({
            "name": "A foreign purchase order",
            "partner_id": self.partner_a.id,
            "company_id": foreign_company.id,
            "order_line": [Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.foreign_currency.id,
            }), Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_order.id,
                "product_qty": 2,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
        })
        purchase_order_foreign.button_confirm()
        self.assertEqual(purchase_order_foreign.invoice_status, 'to invoice')

        # The section "purchase_order" should appear because the purchase order is validated, the total should be updated,
        # but the "other_purchase_costs" shouldn't change, as we don't take into
        # account bills from purchase orders in this section.
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('purchase_order', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['purchase_order'], items['data'][0]['sequence'])
        self.assertEqual(0.0, items['data'][0]['billed'])
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 0.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual('other_purchase_costs', items['data'][1]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][1]['sequence'])
        self.assertEqual(0.0, items['data'][1]['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][1]['billed'], 2), 0)
        self.assertEqual(float_compare(- self.product_order.standard_price * analytic_contribution * 0.6, items['total']['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['total']['billed'], 2), 0)

        # create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            "name": "A foreign purchase order",
            "partner_id": self.partner_a.id,
            "company_id": self.env.company.id,
            "order_line": [Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.env.company.currency_id.id,
            }), Command.create({
                "analytic_distribution": {account.id: analytic_distribution},
                "product_id": self.product_order.id,
                "product_qty": 2,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        self.assertEqual(purchase_order.invoice_status, 'to invoice')

        # The section "purchase_order" should be updated with the new po values.
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('purchase_order', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['purchase_order'], items['data'][0]['sequence'])
        self.assertEqual(0.0, items['data'][0]['billed'])
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 3.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual('other_purchase_costs', items['data'][1]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][1]['sequence'])
        self.assertEqual(0.0, items['data'][1]['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][1]['billed'], 2), 0)
        self.assertEqual(float_compare(- self.product_order.standard_price * analytic_contribution * 3.6    , items['total']['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['total']['billed'], 2), 0)

        self._create_invoice_for_po(purchase_order)
        self.assertEqual(purchase_order.invoice_status, 'invoiced')
        # The section "purchase_order" should now appear because purchase_order was invoiced.
        # The purchase order of the main company has been billed. Its total should now be in the 'billed' section.
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('purchase_order', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['purchase_order'], items['data'][0]['sequence'])
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 0.6, items['data'][0]['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 3, items['data'][0]['billed'], 2), 0)
        self.assertEqual('other_purchase_costs', items['data'][1]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][1]['sequence'])
        self.assertEqual(0.0, items['data'][1]['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][1]['billed'], 2), 0)
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 0.6, items['total']['to_bill'], 2), 0)
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6 - self.product_order.standard_price * analytic_contribution * 3, items['total']['billed'], 2), 0)

        self._create_invoice_for_po(purchase_order_foreign)
        self.assertEqual(purchase_order_foreign.invoice_status, 'invoiced')
        # The purchase order of the main company has been billed. Its total should now be in the 'billed' section.
        # The 'to bill' section of the purchase order should now be empty
        items = project._get_profitability_items(with_action=False)['costs']
        self.assertEqual('purchase_order', items['data'][0]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['purchase_order'], items['data'][0]['sequence'])
        self.assertEqual(0.0, items['data'][0]['to_bill'])
        self.assertEqual(float_compare(-self.product_order.standard_price * analytic_contribution * 3.6, items['data'][0]['billed'], 2), 0)
        self.assertEqual('other_purchase_costs', items['data'][1]['id'])
        self.assertEqual(project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'], items['data'][1]['sequence'])
        self.assertEqual(0.0, items['data'][1]['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6, items['data'][1]['billed'], 2), 0)
        self.assertEqual(0.0, items['total']['to_bill'])
        self.assertEqual(float_compare(-self.product_a.standard_price * analytic_contribution * 3.6 - self.product_order.standard_price * analytic_contribution * 3.6, items['total']['billed'], 2), 0)

    def test_project_purchase_order_smart_button(self):
        project = self.env['project.project'].create({
            'name': 'Test Project'
        })

        purchase_order = self.env['purchase.order'].create({
            "name": "A purchase order",
            "partner_id": self.partner_a.id,
            "company_id": self.env.company.id,
            "order_line": [Command.create({
                "product_id": self.product_order.id,
                "product_qty": 1,
                "price_unit": self.product_order.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
            "project_id": project.id,
        })

        action = project.action_open_project_purchase_orders()
        self.assertTrue(action)
        self.assertEqual(action['res_id'], purchase_order.id)

    def test_analytic_distribution_with_included_tax(self):
        """When calculating the profitability of a project, included taxes should not be calculated"""
        included_tax = self.env['account.tax'].create({
            'name': 'included tax',
            'amount': '15.0',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include_override': 'tax_included',
        })

        # create a purchase.order with the project account in analytic_distribution
        purchase_order = self.env['purchase.order'].create({
            'name': "A purchase order",
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'analytic_distribution': {self.analytic_account.id: 100},
                'product_id': self.product_order.id,
                'product_qty': 2,  # plural value to check if the price is multiplied more than once
                'tax_ids': [included_tax.id],  # set the included tax
                'price_unit': self.product_order.standard_price,
                'currency_id': self.env.company.currency_id.id,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
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
        purchase_order.order_line.product_uom_id = self.env.ref("uom.product_uom_dozen")
        purchase_order.action_create_invoice()
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

    def test_cross_analytics_contribution(self):
        cross_plan = self.env['account.analytic.plan'].create({'name': 'Cross Plan'})
        cross_account = self.env['account.analytic.account'].create({
            'name': "Cross Analytic Account",
            'plan_id': cross_plan.id,
            "company_id": self.env.company.id,
        })
        cross_distribution = 42

        cross_order = self.env['purchase.order'].create({
            'name': 'Cross Purchase Order',
            "partner_id": self.partner_a.id,
            "company_id": self.env.company.id,
            'order_line': [
                Command.create({
                    'analytic_distribution': {
                        f"{self.project.account_id.id},{cross_account.id}": cross_distribution,
                    },
                    "product_id": self.product_order.id,
                    "product_qty": 1,
                    "price_unit": self.product_order.standard_price,
                    "currency_id": self.env.company.currency_id.id,
                }),
            ],
        })

        cross_order.button_confirm()
        cross_order.action_create_invoice()
        items = self.project._get_profitability_items(with_action=False)['costs']
        self.assertEqual(
            items['data'][0]['to_bill'],
            -(self.product_order.standard_price * cross_distribution / 100)
        )

    def test_vendor_credit_note_profitability(self):
        """Reversing a vendor bill should cancel out the profitability costs."""
        purchase_order = self.env['purchase.order'].create({
            'name': "A Purchase",
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'analytic_distribution': {self.analytic_account.id: 100},
                'product_id': self.product_order.id,
            })],
        })
        purchase_order.button_confirm()
        vendor_bill = self._create_invoice_for_po(purchase_order)

        items = self.project._get_profitability_items(with_action=False)['costs']
        self.assertDictEqual(items['total'], {
            'billed': -purchase_order.amount_untaxed,
            'to_bill': 0.0,
        })

        credit_note = vendor_bill._reverse_moves()
        items = self.project._get_profitability_items(with_action=False)['costs']
        self.assertDictEqual(items['total'], {
            'billed': -purchase_order.amount_untaxed,
            'to_bill': purchase_order.amount_untaxed,
        })

        credit_note.invoice_date = vendor_bill.invoice_date
        credit_note.action_post()
        items = self.project._get_profitability_items(with_action=False)['costs']
        self.assertDictEqual(items['total'], {
            'billed': 0.0,
            'to_bill': 0.0,
        })

    def test_project_purchase_profitability_without_analytic_distribution(self):
        purchase_order = self.env['purchase.order'].create({
            "name": "A purchase order",
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                'analytic_distribution': {self.analytic_account.id: 100},
                'product_id': self.product_order.id,
            })],
        })
        purchase_order.button_confirm()

        vendor_bill = self._create_invoice_for_po(purchase_order)
        vendor_bill.invoice_line_ids.analytic_distribution = False

        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'purchase_order',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['purchase_order'],
                    'to_bill': 0.0,
                    'billed': 0.0,
                }],
                'total': {
                    'to_bill': 0.0,
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
