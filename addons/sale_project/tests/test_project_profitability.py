# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

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
        cls.uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product_delivery_service = cls.env['product.product'].create({
            'name': "Service Delivery, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'manual',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.project.id,
        })
        cls.down_payment_product = cls.env['product.product'].create({
            'name': "downpayment product, used to simulate down payments",
            'standard_price': 30,
            'type': 'service',
            'service_policy': 'ordered_prepaid',
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
            'account_id': cls.analytic_account_nb.id,
            'allow_billable': False,
            'partner_id': False,
        })
        cls.project_billable_no_company = cls.env['project.project'].create({'name': 'project billable', 'allow_billable': True})
        cls.project_billable_no_company._create_analytic_account()


@tagged('-at_install', 'post_install')
class TestSaleProjectProfitability(TestProjectProfitabilityCommon, TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    def test_profitability_of_non_billable_project(self):
        """ Test no data is found for the project profitability since the project is not billable
            even if it is linked to a sale order items.
        """
        # Adding an extra cost/revenue to ensure those are not computed either.
        self.env['account.analytic.line'].create([{
            'name': 'other revenues line',
            'account_id': self.project_non_billable.account_id.id,
            'amount': 100,
        }, {
            'name': 'other costs line',
            'account_id': self.project_non_billable.account_id.id,
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
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        companies = foreign_company | self.sale_order.company_id
        self.project.company_id = False
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

        # Add extra cost and extra revenues to the analytic account.
        self.env['account.analytic.line'].create([{
            'name': 'other revenues line',
            'account_id': self.project.account_id.id,
            'amount': 100,
        }, {
            'name': 'other costs line',
            'account_id': self.project.account_id.id,
            'amount': -100,
        }])

        # Create and confirm a SO in a foreign company.
        product_delivery_service_foreign = self.env['product.product'].with_company(foreign_company).create({
            'name': "Service Delivery, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'manual',
            'uom_id': self.uom_hour.id,
            'uom_po_id': self.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': self.project.id,
        })
        sale_order_foreign = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'company_id': foreign_company.id,
        })
        sale_order_foreign.currency_id = self.foreign_currency.id
        sol_foreign = self.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=sale_order_foreign.id).create({
            'product_id': product_delivery_service_foreign.id,
            'product_uom_qty': 10,
            'company_id': foreign_company.id,
        })
        sale_order_foreign.action_confirm()
        sol_foreign.qty_delivered = 1
        service_policy_to_invoice_type = self.project._get_service_policy_to_invoice_type()
        invoice_type = service_policy_to_invoice_type[self.delivery_service_order_line.product_id.service_policy]
        self.assertIn(
            invoice_type,
            ['billable_manual', 'service_revenues'],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"')
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        # Ensures that when the only SO linked to the project is a foreign SO, the currency used is the default one, and not the currency of the SO.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            # id should be equal to "billable_manual" if "sale_timesheet" module is installed otherwise "service_revenues"
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': 0.0,
                        },
                    ],
                    'total': {
                        'to_invoice': sol_foreign.untaxed_amount_to_invoice * 0.2,
                        'invoiced': 100.0,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )
        self.assertNotEqual(sol_foreign.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(sol_foreign.untaxed_amount_invoiced, 0.0)

        # Set the qty_delivered of the sol of the main so to 1, this sol should now be computed for the project_profitability.
        self.delivery_service_order_line.qty_delivered = 1
        self.assertIn('service_revenues', sequence_per_invoice_type)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            # id should be equal to "billable_manual" if "sale_timesheet" module is installed otherwise "service_revenues"
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice + sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': 0.0,
                        },
                    ],
                    'total': {
                        'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice + sol_foreign.untaxed_amount_to_invoice * 0.2,
                        'invoiced': 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )
        self.assertNotEqual(self.delivery_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(self.delivery_service_order_line.untaxed_amount_invoiced, 0.0)

        # Create and post an invoice for the foreign SO.
        context = {
            'active_model': 'sale.order',
            'active_ids': sale_order_foreign.ids,
            'active_id': sale_order_foreign.id,
            'allowed_company_ids': companies.ids,
        }
        invoices_foreign = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })._create_invoices(sale_order_foreign)
        invoices_foreign.action_post()
        # Ensures the foreign SO sols are now computed for the 'invoiced' section, while the sol's from the main SO are still in the 'to_invoice' section
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            # id should be equal to "billable_manual" if "sale_timesheet" module is installed otherwise "service_revenues"
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice,
                            'invoiced': sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': self.delivery_service_order_line.untaxed_amount_to_invoice,
                        'invoiced': 100 + sol_foreign.untaxed_amount_invoiced * 0.2,
                    },
                },
                'costs': {
                    'data': [
                        {'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0,
                         'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )
        self.assertEqual(sol_foreign.qty_invoiced, 1)
        self.assertEqual(sol_foreign.untaxed_amount_to_invoice, 0.0)
        self.assertNotEqual(sol_foreign.untaxed_amount_invoiced, 0.0)

        # Create and post an invoice for the main SO.
        context = {
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
            'active_id': self.sale_order.id,
        }
        invoices = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })._create_invoices(self.sale_order)
        invoices.action_post()
        invoice_type = service_policy_to_invoice_type[self.delivery_service_order_line.product_id.service_policy]
        self.assertIn(
            invoice_type,
            ['billable_manual', 'service_revenues'],
            'invoice_type="billable_manual" if sale_timesheet is installed otherwise it is equal to "service_revenues"')
        # Ensures that the 'to_invoice' section is now empty, and the 'invoiced' section contains the amount from all the sol's.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': 0.0,
                            'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': 0.0,
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + 100 + sol_foreign.untaxed_amount_invoiced * 0.2,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            }
        )
        self.assertEqual(self.delivery_service_order_line.qty_invoiced, 1)
        self.assertEqual(self.delivery_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertNotEqual(self.delivery_service_order_line.untaxed_amount_invoiced, 0.0)

        # Add 2 sale order item to the foreign SO.
        SaleOrderLineForeign = self.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=sale_order_foreign.id)
        manual_service_sol_foreign, material_sol_foreign = SaleOrderLineForeign.create([{
            'product_id': self.product_delivery_service.id,
            'product_uom_qty': 5,
            'qty_delivered': 5,
        }, {
            'product_id': self.material_product.id,
            'product_uom_qty': 1,
            'qty_delivered': 1,
        }])
        service_sols_foreign = sol_foreign + manual_service_sol_foreign
        # Ensures that the 'materials' section is now present, and that the new manual sol is computed in the 'to_invoice' section.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) * 0.2,
                            'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) * 0.2,
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': material_sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': (sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) + material_sol_foreign.untaxed_amount_to_invoice) * 0.2,
                        'invoiced': self.delivery_service_order_line.untaxed_amount_invoiced + (sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) + material_sol_foreign.untaxed_amount_invoiced) * 0.2 + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        self.assertNotEqual(manual_service_sol_foreign.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(manual_service_sol_foreign.untaxed_amount_invoiced, 0.0)
        self.assertNotEqual(material_sol_foreign.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(material_sol_foreign.untaxed_amount_invoiced, 0.0)
        # Add 2 sales order items in the main SO.
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
        # Ensures that the 'materials' section contains the material sol from the main company, and that the new manual sol is computed in the 'to_invoice' section.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) * 0.2,
                            'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) * 0.2,
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice + material_sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': material_order_line.untaxed_amount_invoiced + material_sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice +
                                      (sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) + material_sol_foreign.untaxed_amount_to_invoice) * 0.2,
                        'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + material_order_line.untaxed_amount_invoiced +
                                    (sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) + material_sol_foreign.untaxed_amount_invoiced) * 0.2 + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        self.assertNotEqual(manual_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(manual_service_order_line.untaxed_amount_invoiced, 0.0)
        self.assertNotEqual(material_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(material_order_line.untaxed_amount_invoiced, 0.0)

        # Revert the invoice from the foreign SO.
        credit_notes = invoices_foreign._reverse_moves()
        credit_notes.action_post()
        # Ensures that the sols that were invoiced are computed in the 'to_invoice' section again.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) * 0.2,
                            'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) * 0.2,
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice + material_sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': material_order_line.untaxed_amount_invoiced + material_sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice +
                                      (sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) + material_sol_foreign.untaxed_amount_to_invoice) * 0.2,
                        'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + material_order_line.untaxed_amount_invoiced +
                                    (sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) + material_sol_foreign.untaxed_amount_invoiced) * 0.2 + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        self.assertEqual(sol_foreign.qty_invoiced, 0.0)
        self.assertNotEqual(sol_foreign.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(sol_foreign.untaxed_amount_invoiced, 0.0)

        # Revert the invoice from the main SO.
        credit_notes = invoices._reverse_moves()
        credit_notes.action_post()
        # Ensures that the sols that were invoiced are computed in the 'to_invoice' section again.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) * 0.2,
                            'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) * 0.2,
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'to_invoice': material_order_line.untaxed_amount_to_invoice + material_sol_foreign.untaxed_amount_to_invoice * 0.2,
                            'invoiced': material_order_line.untaxed_amount_invoiced + material_sol_foreign.untaxed_amount_invoiced * 0.2,
                        },
                    ],
                    'total': {
                        'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice +
                                      (sum(service_sols_foreign.mapped('untaxed_amount_to_invoice')) + material_sol_foreign.untaxed_amount_to_invoice) * 0.2,
                        'invoiced': sum(service_sols.mapped('untaxed_amount_invoiced')) + material_order_line.untaxed_amount_invoiced +
                                    (sum(service_sols_foreign.mapped('untaxed_amount_invoiced')) + material_sol_foreign.untaxed_amount_invoiced) * 0.2 + 100,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        self.assertEqual(self.delivery_service_order_line.qty_invoiced, 0.0)
        self.assertNotEqual(self.delivery_service_order_line.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(self.delivery_service_order_line.untaxed_amount_invoiced, 0.0)

        # Cancel the foreign SO.
        sale_order_foreign._action_cancel()
        # Ensures that the panel now contains only the sols from the main SO.
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
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
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        # Create a down payment for a fixed amount of 115.
        Downpayment = {
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(Downpayment).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 115,
        })
        # When a down payment is created, the default 15% tax is included. The SOL associated it then created by removing the taxed amount.
        # Therefore, the amount of the dp is higher than the amount of the sol created.
        down_payment_invoiced = 100.00
        downpayment.create_invoices()
        self.sale_order.invoice_ids[2].action_post()
        # Ensures the down payment is correctly computed for the project profitability.
        self._assert_dict_equal(invoice_type, sequence_per_invoice_type, material_order_line, service_sols, manual_service_order_line, down_payment_invoiced)

        # Create a second down payment for a fixed amount of 115.
        downpayment = self.env['sale.advance.payment.inv'].with_context(Downpayment).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 115,
        })
        down_payment_invoiced = 2 * down_payment_invoiced
        downpayment.create_invoices()
        self.sale_order.invoice_ids[3].action_post()
        # Ensures the 2 down payments are correctly computed for the project profitability.
        self._assert_dict_equal(invoice_type, sequence_per_invoice_type, material_order_line, service_sols, manual_service_order_line, down_payment_invoiced)

        for sol in sale_order_foreign.order_line:
            self.assertEqual(sol.untaxed_amount_to_invoice, 0.0)
            self.assertEqual(sol.untaxed_amount_invoiced, 0.0)

        # Cancel the main SO.
        self.sale_order._action_cancel()
        # Ensures that the panel no longer contains any SOL related section
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                # even if the sale order is canceled, if some expenses/revenues were added manually to the account, those lines must appear in the project profitabilty panel
                'revenues': {
                    'data': [
                        {'id': 'other_revenues_aal', 'sequence': sequence_per_invoice_type['other_revenues_aal'], 'invoiced': 100.0, 'to_invoice': 0.0}],
                    'total': {'to_invoice': 0.0, 'invoiced': 100},
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
                    'total': {'billed': -100.0, 'to_bill': 0.0},
                },
            },
        )
        #downpayment invoiced amount are not updated when the SO is canceled.
        for sol in self.sale_order.order_line:
            if sol.is_downpayment:
                continue
            self.assertEqual(sol.untaxed_amount_to_invoice, 0.0)
            self.assertEqual(sol.untaxed_amount_invoiced, 0.0)

    def _assert_dict_equal(self, invoice_type, sequence_per_invoice_type, material_order_line, service_sols, manual_service_order_line, down_payment_invoiced):
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [
                        {
                            'id': 'other_revenues_aal',
                            'sequence': sequence_per_invoice_type['other_revenues_aal'],
                            'invoiced': 100.0,
                            'to_invoice': 0.0,
                        },
                        {
                            'id': 'downpayments', 'sequence': 20, 'invoiced': down_payment_invoiced,
                            'to_invoice': -down_payment_invoiced,
                        },
                        {
                            'id': invoice_type,
                            'sequence': sequence_per_invoice_type[invoice_type],
                            'invoiced': manual_service_order_line.untaxed_amount_invoiced,
                            'to_invoice': sum(service_sols.mapped('untaxed_amount_to_invoice')),
                        },
                        {
                            'id': 'materials',
                            'sequence': sequence_per_invoice_type['materials'],
                            'invoiced': material_order_line.untaxed_amount_invoiced,
                            'to_invoice': material_order_line.untaxed_amount_to_invoice,
                        },
                    ],
                    'total': {
                        'invoiced': manual_service_order_line.untaxed_amount_invoiced + material_order_line.untaxed_amount_invoiced + down_payment_invoiced + 100,
                        'to_invoice': sum(service_sols.mapped(
                            'untaxed_amount_to_invoice')) + material_order_line.untaxed_amount_to_invoice - down_payment_invoiced,
                    },
                },
                'costs': {
                    'data': [{'id': 'other_costs_aal', 'sequence': sequence_per_invoice_type['other_costs_aal'], 'billed': -100.0, 'to_bill': 0.0}],
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
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        # a custom analytic contribution (number between 1 -> 100 included)
        analytic_distribution = 50
        analytic_contribution = analytic_distribution / 100.
        # Create an invoice with a foreign company with the AAL linked to the project account.
        invoice_1_foreign = self.env['account.move'].create({
            "name": "Invoice_1",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "company_id": foreign_company.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
        })
        # The invoice with foreign company is in draft, therefore its total is in the 'to invoice' section. The total should be update by the choas orb/dollar rate (0.2)
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': self.product_a.standard_price * analytic_contribution * 0.2,
                    'invoiced': 0.0,
                }],
                'total': {'to_invoice': self.product_a.standard_price * analytic_contribution * 0.2, 'invoiced': 0.0},
            },
        )
        # Create an invoice_1 with the AAL linked to the project account.
        invoice_1 = self.env['account.move'].create({
            "name": "Invoice_1",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            })],
        })
        # The invoice_1 is in draft, therefore its total should be added to the 'to_invoice' section.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': self.product_a.standard_price * analytic_contribution * 1.2,
                    'invoiced': 0.0,
                }],
                'total': {'to_invoice': self.product_a.standard_price * analytic_contribution * 1.2, 'invoiced': 0.0},
            },
        )
        # post invoice_1
        invoice_1.action_post()
        # We posted the invoice_1, therefore its total should be in the 'invoiced' section. The 'to_invoice' section should now contain only the foreign invoice.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': self.product_a.standard_price * analytic_contribution * 0.2,
                    'invoiced': self.product_a.standard_price * analytic_contribution,
                }],
                'total': {'to_invoice': self.product_a.standard_price * analytic_contribution * 0.2, 'invoiced': self.product_a.standard_price * analytic_contribution},
            },
        )
        invoice_1_foreign.action_post()
        # We posted the foreign invoice 1. Its total should now be in the 'invoiced' section. The 'to_invoice' section should be 0.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': 0.0,
                    'invoiced': self.product_a.standard_price * analytic_contribution * 1.2,
                }],
                'total': {'to_invoice': 0.0, 'invoiced': self.product_a.standard_price * analytic_contribution * 1.2},
            },
        )

        # Ensures the sale_line_ids from multiple invoices from the same company are correctly computed.
        # Create another invoice, with 2 lines, 2 diff products, the second line has a quantity of 2, the third line has a negative amount
        NEG_AMOUNT = -42
        invoice_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            }), Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
            }), Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_b.id,
                "quantity": 1,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": NEG_AMOUNT,
            })],
        })
        # The invoice_2 is not posted, therefore its cost should be in the "to_invoice" section
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                    'invoiced': self.product_a.standard_price * analytic_contribution * 1.2,
                }],
                'total': {
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                    'invoiced': self.product_a.standard_price * analytic_contribution * 1.2,
                },
            },
        )
        # post invoice_2
        invoice_2.action_post()
        # The invoice_2 is posted, therefore its cost should be in the "invoiced" section
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': 0.0,
                    'invoiced': (2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                }],
                'total': {
                    'to_invoice': 0.0,
                    'invoiced': (2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                },
            },
        )
        # Create another invoice, with 2 lines, 2 diff products, the second line has a quantity of 2 with a foreign company.
        invoice_2_foreign = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "out_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "company_id": foreign_company.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id,
            }), Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: analytic_distribution},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
        })
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['revenues'],
            {
                'data': [{
                    'id': 'other_invoice_revenues',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'],
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price) * analytic_contribution * 0.2,
                    'invoiced': (2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                }],
                'total': {
                    'to_invoice': (self.product_a.standard_price + 2 * self.product_b.standard_price) * analytic_contribution * 0.2,
                    'invoiced': (2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price + NEG_AMOUNT) * analytic_contribution,
                },
            },
        )
        invoice_2_foreign.action_post()
        # Note : for some reason, the method to round the amount to the rounding of the currency is not 100% reliable.
        # We use a float_compare in order to ensure the value is close enough to the expected result. This problem has no repercusion on the client side, since
        # there is also a rounding method on this side to ensure the amount is correctly displayed.
        items = self.project_billable_no_company._get_profitability_items(False)['revenues']
        self.assertEqual(float_compare(((self.product_a.standard_price + self.product_b.standard_price) * 2.4 + NEG_AMOUNT) * analytic_contribution, items['data'][0]['invoiced'], 2), 0)
        self.assertEqual(float_compare(((self.product_a.standard_price + self.product_b.standard_price) * 2.4 + NEG_AMOUNT) * analytic_contribution, items['total']['invoiced'], 2), 0)
        self.assertEqual(items['data'][0]['id'], 'other_invoice_revenues')
        self.assertEqual(items['data'][0]['sequence'], self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_invoice_revenues'])
        self.assertEqual(items['data'][0]['to_invoice'], 0.0)
        self.assertEqual(items['total']['to_invoice'], 0.0)

    def test_bills_without_purchase_order_are_accounted_in_profitability_sale_project(self):
        """
        A bill that has an AAL on one of its line should be taken into account
        for the profitability of the project.
        """
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency

        # Create a bill with its purchase line linked to the AA of the project, and a foreign company.
        bill_1_foreign = self.env['account.move'].create({
            "name": "Bill_1 name",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "company_id": foreign_company.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id
            })],
        })
        # Add 2 new AAL to the analytic account. Those costs must be present in the 'other_cost' section
        self.env['account.analytic.line'].create([{
            'name': 'extra costs 1',
            'account_id': self.project_billable_no_company.account_id.id,
            'amount': -50,
        }, {
            'name': 'extra costs 2',
            'account_id': self.project_billable_no_company.account_id.id,
            'amount': -100,
        }])
        # Ensures that the amount of the 'other_purchase_cost' is correctly scale to the currency of the main company.
        # Ensures that the 'other_cost' is not mixed within the 'other_purchase_costs' section and vice-versa
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price * 0.2,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price * 0.2, 'billed': -150.0},
            },
        )
        # Create a bill with its purchase line linked to the AA of the project, and the main company.
        bill_1 = self.env['account.move'].create({
            "name": "Bill_1 name",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            })],
        })
        # Ensures that the amount from the bill_1 is in the 'to_bill' section of the 'other_purchase_cost'
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price * 1.2,
                    'billed': 0.0,
                }],
                'total': {'to_bill': -self.product_a.standard_price * 1.2, 'billed': -150.0},
            },
        )
        # post bill_1
        bill_1.action_post()
        # We posted the bill_1, therefore its cost should now be in the 'billed' section.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -self.product_a.standard_price * 0.2,
                    'billed': -self.product_a.standard_price,
                }],
                'total': {'to_bill': -self.product_a.standard_price * 0.2, 'billed': -self.product_a.standard_price - 150},
            },
        )
        bill_1_foreign.action_post()
        # We posted the bill_1_foreign, therefore its cost should now be in the 'billed' section.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -self.product_a.standard_price * 1.2,
                }],
                'total': {'to_bill': 0.0, 'billed': -self.product_a.standard_price * 1.2 - 150},
            },
        )
        # Create another bill, with 2 lines, 2 different products and different quantities
        bill_2 = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
            }), Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
            })],
        })
        # Ensures that when there are more than one bill/move_line from one company, all the lines are computed.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price * 1.2,
                }],
                'total': {
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price),
                    'billed': -self.product_a.standard_price * 1.2 - 150,
                },
            },
        )
        # post bill_2
        bill_2.action_post()
        # The bill_2 is posted, therefore its cost should now be in the 'billed' section.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -(2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -(2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price) - 150,
                },
            },
        )
        # Create another bill, with 2 lines, 2 different products, different quantities and a foreign company.
        bill_2_foreign = self.env['account.move'].create({
            "name": "I have 2 lines",
            "move_type": "in_invoice",
            "state": "draft",
            "partner_id": self.partner.id,
            "invoice_date": datetime.today(),
            "company_id": foreign_company.id,
            "invoice_line_ids": [Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_a.id,
                "quantity": 1,
                "product_uom_id": self.product_a.uom_id.id,
                "price_unit": self.product_a.standard_price,
                "currency_id": self.foreign_currency.id,
            }), Command.create({
                "analytic_distribution": {self.project_billable_no_company.account_id.id: 100},
                "product_id": self.product_b.id,
                "quantity": 2,
                "product_uom_id": self.product_b.uom_id.id,
                "price_unit": self.product_b.standard_price,
                "currency_id": self.foreign_currency.id,
            })],
        })
        # Ensures that when there are more than one bill/move_line from one company, all the lines are computed and correctly scaled with the currency of the main company.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()['other_purchase_costs'],
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price) * 0.2,
                    'billed': -(2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': -(self.product_a.standard_price + 2 * self.product_b.standard_price) * 0.2,
                    'billed': -(2.2 * self.product_a.standard_price + 2 * self.product_b.standard_price) - 150,
                },
            },
        )
        # post bill_2_foreign
        bill_2_foreign.action_post()
        # The bill_2_foreign is posted, therefore its cost should now be in the 'billed' section.
        self.assertDictEqual(
            self.project_billable_no_company._get_profitability_items(False)['costs'],
            {
                'data': [{
                    'id': 'other_costs_aal',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                        'other_costs_aal'],
                    'to_bill': 0.0,
                    'billed': -150.0,
                }, {
                    'id': 'other_purchase_costs',
                    'sequence': self.project_billable_no_company._get_profitability_sequence_per_invoice_type()[
                        'other_purchase_costs'],
                    'to_bill': 0.0,
                    'billed': -2.4 * (self.product_a.standard_price + self.product_b.standard_price),
                }],
                'total': {
                    'to_bill': 0.0,
                    'billed': -2.4 * (self.product_a.standard_price + self.product_b.standard_price) - 150,
                },
            },
        )
