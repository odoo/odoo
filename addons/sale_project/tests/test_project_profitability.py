# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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


@tagged('-at_install', 'post_install')
class TestSaleProjectProfitability(TestProjectProfitabilityCommon, TestSaleCommon):
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
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
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
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced,
                    },
                },
                'costs': {
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0},
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
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': 0.0,
                            'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': 0.0,
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced,
                    },
                },
                'costs': {
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0},
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
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')),
                            'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')),
                        },
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice,
                            'invoiced': material_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice,
                        'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + material_order_line.untaxed_amount_invoiced,
                    },
                },
                'costs': {  # no cost because we have no purchase orders.
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0},
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
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')),
                            'invoiced': manual_service_order_line.untaxed_amount_invoiced,
                        },
                        {
                            'id': 'other_revenues',
                            'sequence': sequence_per_invoice_type['other_revenues'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice,
                            'invoiced': material_order_line.untaxed_amount_invoiced,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice,
                        'invoiced': manual_service_order_line.untaxed_amount_invoiced + material_order_line.untaxed_amount_invoiced,
                    },
                },
                'costs': {  # no cost because we have no purchase orders.
                    'data': [],
                    'total': {'billed': 0.0, 'to_bill': 0.0},
                },
            },
        )

        self.sale_order._action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
        )
