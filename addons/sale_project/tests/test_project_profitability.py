# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon as Common


class TestProjectProfitabilityCommon(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uom_unit_id = cls.env.ref('uom.product_uom_unit').id

        # Create material product
        cls.material_product = cls.env['product.product'].create({
            'name': 'Material',
            'type': 'consu',
            'standard_price': 5,
            'list_price': 10,
            'invoice_policy': 'order',
            'uom_id': uom_unit_id,
            'uom_po_id': uom_unit_id,
        })

        # Create service products
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product_delivery_service = cls.env['product.product'].create({
            'name': "Service Delivery, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'manual',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.project.id,
        })
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id,
            'partner_shipping_id': cls.partner.id,
        })
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=cls.sale_order.id)
        cls.delivery_service_order_line = SaleOrderLine.create({
            'product_id': cls.product_delivery_service.id,
            'product_uom_qty': 10,
        })
        cls.sale_order.action_confirm()

        cls.analytic_account_nb = cls.env['account.analytic.account'].create({
            'name': 'Project non billable AA',
            'code': 'AA-123456',
            'plan_id': cls.analytic_plan.id,
        })

        cls.project_non_billable = cls.env['project.project'].with_context(tracking_disable=True).create({
            'name': "Non Billable Project",
            'analytic_account_id': cls.analytic_account_nb.id,
            'allow_billable': False,
            'partner_id': False,
        })


@tagged('-at_install', 'post_install')
class TestSaleProjectProfitability(TestProjectProfitabilityCommon, TestSaleCommon):

    def test_profitability_of_non_billable_project(self):
        """ Test no data is found for the project profitability since the project is not billable
            even if it is linked to a sale order items.
        """
        # Adding an extra cost/revenue to ensure those are not computed either.
        self.env['account.analytic.line'].create([{
            'name': 'other revenues line',
            'account_id': self.project_non_billable.analytic_account_id.id,
            'amount': 100,
        }, {
            'name': 'other costs line',
            'account_id': self.project_non_billable.analytic_account_id.id,
            'amount': -100,
        }])
        self.assertFalse(self.project_non_billable.allow_billable)
        panel_data = self.project_non_billable.get_panel_data()
        self.assertFalse(panel_data.get('profitability_items'))
        self.assertFalse(panel_data.get('profitability_labels'))
        self.project_non_billable.write({'sale_line_id': self.sale_order.order_line[0].id})
        panel_data = self.project_non_billable.get_panel_data()
        self.assertFalse(panel_data.get('profitability_items'),
                         "Even if the project has a sale order item linked, the project profitability should not be computed since it is not billable.")
        self.assertFalse(panel_data.get('profitability_labels'),
                         "Even if the project has a sale order item linked, the project profitability should not be computed since it is not billable.")

    def test_project_profitability(self):
        self.assertFalse(self.project.allow_billable, 'The project should be non billable.')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data for the project profitability should be found since the project is not billable, so no SOL is linked to the project.'
        )
        self.project.write({'allow_billable': True})
        self.assertTrue(self.project.allow_billable, 'The project should be billable.')
        self.project.sale_line_id = self.delivery_service_order_line
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data for the project profitability should be found since no product is delivered in the SO linked.'
        )
        self.delivery_service_order_line.qty_delivered = 1
        service_policy_to_invoice_type = self.project._get_service_policy_to_invoice_type()
        invoice_type = service_policy_to_invoice_type[self.delivery_service_order_line.product_id.service_policy]
        self.assertIn(
            invoice_type,
            ['billable_manual', 'service_revenues'],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"')
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('service_revenues', sequence_per_invoice_type)

        #we're adding extra cost and extra revenues to the analytic account
        self.env['account.analytic.line'].create([{
            'name': 'other revenues line',
            'account_id': self.project.analytic_account_id.id,
            'amount': 100,
        }, {
            'name': 'other costs line',
            'account_id': self.project.analytic_account_id.id,
            'amount': -100,
        }])
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            # id should be equal to "billable_manual" if "sale_timesheet" module is installed otherwise "service_revenues"
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice,
                            'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice,
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )
        self.assertNotEqual(self.delivery_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(self.delivery_service_order_line.untaxed_amount_invoiced, 0.0)

        # create an invoice
        context = {
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
            'active_id': self.sale_order.id,
        }
        invoices = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })._create_invoices(self.sale_order)
        invoices.action_post()

        self.assertEqual(self.delivery_service_order_line.qty_invoiced, 1)
        self.assertEqual(self.delivery_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertNotEqual(self.delivery_service_order_line.untaxed_amount_invoiced, 0.0)
        invoice_type = service_policy_to_invoice_type[self.delivery_service_order_line.product_id.service_policy]
        self.assertIn(
            invoice_type,
            ['billable_manual', 'service_revenues'],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': 0.0,
                            'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': 0.0,
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )

        # Add 2 sales order items in the SO
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=self.sale_order.id)
        manual_service_order_line = SaleOrderLine.create({
            'product_id': self.product_delivery_service.id,
            'product_uom_qty': 5,
            'qty_delivered': 5,
        })
        material_order_line = SaleOrderLine.create({
            'product_id': self.material_product.id,
            'product_uom_qty': 1,
            'qty_delivered': 1,
        })
        service_sols = self.delivery_service_order_line + manual_service_order_line
        invoice_type = service_policy_to_invoice_type[manual_service_order_line.product_id.service_policy]
        self.assertIn(
            invoice_type,
            ['billable_manual', 'service_revenues'],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')),
                            'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')),
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice,
                            'invoiced': material_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice,
                        'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + material_order_line.untaxed_amount_invoiced + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        self.assertNotEqual(manual_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(manual_service_order_line.untaxed_amount_invoiced, 0.0)
        self.assertNotEqual(material_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(material_order_line.untaxed_amount_invoiced, 0.0)

        credit_notes = invoices._reverse_moves()
        credit_notes.action_post()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')),
                            'invoiced': manual_service_order_line.untaxed_amount_invoiced,
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice,
                            'invoiced': material_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice,
                        'invoiced': manual_service_order_line.untaxed_amount_invoiced + material_order_line.untaxed_amount_invoiced + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )

        self.sale_order._action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                # even if the sale order is canceled, if some expenses/revenues were added manually to the account, those lines must appear in the project profitabilty panel
                'revenues': {
                    'data': [
                        {'id': 'other_revenues', 'sequence': sequence_per_invoice_type['other_revenues'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'to_invoice': 0.0, 'invoiced': 100},
                },
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': sequence_per_invoice_type['other_costs'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )

    def test_invoices_without_sale_order_are_accounted_in_profitability(self):
        """
        An invoice that has an AAL on one of its line should be taken into account
        for the profitability of the project.
        The contribution of the line should only be dependent
        on the project's analytic account % that was set on the line
        """
        self.project.allow_billable = True
        # a custom analytic contribution (number between 1 -> 100 included)
        analytic_distribution = 42
        analytic_contribution = analytic_distribution / 100.
        # create an invoice_1 with the AAL
        invoice_1 = self.env['account.move'].create({
            "name": "Invoice_1",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            })],
        })
        # the bill_1 is in draft, therefore it should have the cost "to_invoice" same as the -product_price (untaxed)
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': self.product_a.standard_price * analytic_contribution,
                    'invoiced': 0.0,
                }],
                'total': {'to_invoice': self.product_a.standard_price * analytic_contribution, 'invoiced': 0.0},
            },
        )
        # post invoice_1
        invoice_1.action_post()
        # we posted the invoice_1, therefore the revenue "invoiced" should be -product_price, to_invoice should be back to 0
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': 0.0,
                    'invoiced': self.product_a.standard_price * analytic_contribution,
                }],
                'total': {'to_invoice': 0.0, 'invoiced': self.product_a.standard_price * analytic_contribution},
            },
        )
        # create another invoice, with 2 lines, 2 diff products, the second line has 2 as quantity
        invoice_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            }), Command.create({
                "analytic_distribution": {self.analytic_account.id: analytic_distribution},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
            })],
        })
        # invoice_2 is not posted, therefore its cost should be "to_invoice" = - sum of all product_price * qty for each line
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price) * analytic_contribution,
                    'invoiced': self.product_a.standard_price * analytic_contribution,
                }],
                'total': {
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price) * analytic_contribution,
                    'invoiced': self.product_a.standard_price * analytic_contribution,
                },
            },
        )
        # post invoice_2
        invoice_2.action_post()
        # invoice_2 is posted, therefore its revenue should be counting in "invoiced", with the revenues from invoice_1
        self.assertDictEqual(
            self.project._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': 0.0,
                    'invoiced': 2 * (self.product_a.standard_price + self.product_b.standard_price) * analytic_contribution,
                }],
                'total': {
                    'to_invoice': 0.0,
                    'invoiced': 2 * (self.product_a.standard_price + self.product_b.standard_price) * analytic_contribution,
                },
            },
        )

    def test_bills_without_purchase_order_are_accounted_in_profitability_sale_project(self):
        """
        A bill that has an AAL on one of its line should be taken into account
        for the profitability of the project.
        """
        # create a bill_1 with the AAL
        bill_1 = self.env['account.move'].create({
            "name": "Bill_1 name",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            })],
        })
        # add 2 new AAL to the analytic account. Those costs must be present in the cost data
        self.env['account.analytic.line'].create([{
            'name': 'extra costs 1',
            'account_id': self.analytic_account.id,
            'amount': -50,
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
                    'id': 'other_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price, 'billed': -150.0},
            },
        )
        # post bill_1
        bill_1.action_post()
        # we posted the bill_1, therefore the cost "billed" should be -product_price, to_bill should be back to 0
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -self.product_a.standard_price,
                }],
                'total': {'to_bill': 0.0, 'billed': -self.product_a.standard_price - 150},
            },
        )
        # create another bill, with 2 lines, 2 diff products, the second line has 2 as quantity
        bill_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.analytic_account.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            }), Command.create({
                "analytic_distribution": {self.analytic_account.id: 100},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
            })],
        })
        # bill_2 is not posted, therefore its cost should be "to_billed" = - sum of all product_price * qty for each line
        self.assertDictEqual(
            self.project._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price,
                }],
                'total': {
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price - 150,
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
                    'id': 'other_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_costs'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -2 * (self.product_a.standard_price + self.product_b.standard_price) - 150,
                },
            },
        )
