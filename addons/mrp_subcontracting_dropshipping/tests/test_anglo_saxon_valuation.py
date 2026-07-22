# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo import Command, fields
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSubcontractingDropshippingValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categ_form = Form(cls.env['product.category'])
        categ_form.name = 'fifo auto'
        categ_form.property_cost_method = 'fifo'
        categ_form.property_valuation = 'real_time'
        cls.categ_fifo_auto = categ_form.save()

        categ_form = Form(cls.env['product.category'])
        categ_form.name = 'avco auto'
        categ_form.property_cost_method = 'average'
        categ_form.property_valuation = 'real_time'
        cls.categ_avco_auto = categ_form.save()

        (cls.product_a | cls.product_b).is_storable = True

        cls.dropship_route = cls.env.ref('stock_dropshipping.route_drop_shipping')

        cls.bom_a = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_a.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, cls.partner_a.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_b.id, 'product_qty': 1.0}),
            ],
        })

    def test_valuation_subcontracted_and_dropshipped(self):
        """A product that is both subcontracted and dropshipped is produced by the
        subcontractor and shipped straight to the customer. It is valued at the
        subcontractor fee plus the component cost as it is produced, but since it
        never enters the company's own stock the dropship move is unvalued and the
        product keeps a zero on-hand value.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.subcontracting_to_resupply = True
        (self.product_a | self.product_b).categ_id = self.categ_fifo_auto
        self.product_b.standard_price = 10
        self.env['product.supplierinfo'].create({
            'partner_id': self.partner_a.id,
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'price': 100,
        })
        self.env['stock.quant']._update_available_quantity(self.product_b, warehouse.lot_stock_id, 5.0)

        dropship_picking_type = self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id.usage', '=', 'customer'),
        ], order='sequence', limit=1)
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'picking_type_id': dropship_picking_type.id,
            'dest_address_id': self.partner_b.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id, 'product_qty': 2.0, 'price_unit': 100, 'tax_ids': False,
            })],
        })
        po.button_confirm()

        # resupply the subcontractor with the component, then ship to the customer
        production = po.reference_ids.production_ids
        production.picking_ids.button_validate()
        dropship = po.picking_ids
        dropship.button_validate()

        # the finished move is valued at subcontractor fee + component (2 * (100 + 10))
        self.assertRecordValues(production.move_finished_ids, [
            {'value': 220.0, 'is_in': True, 'is_valued': True},
        ])
        # the component is consumed from own stock
        self.assertRecordValues(production.move_raw_ids, [
            {'value': 20.0, 'is_out': True, 'is_valued': True},
        ])
        # the goods ship straight to the customer: the dropship move is unvalued
        self.assertRecordValues(dropship.move_ids, [
            {'value': 0.0, 'is_dropship': True, 'is_valued': False},
        ])
        # nothing enters own stock, so no on-hand value; the unit cost still reflects
        # the subcontracted cost
        self.assertRecordValues(self.product_a, [
            {'total_value': 0.0, 'qty_available': 0.0, 'standard_price': 110.0},
        ])
        self.assertFalse(dropship.move_ids.account_move_id)

    def test_account_line_entry_kit_bom_dropship(self):
        """ An order delivered via dropship for some kit bom product variant should result in
        accurate journal entries in the expense and stock output accounts if the cost on the
        purchase order line has been manually edited.
        """
        kit_final_prod = self.product_a
        product_c = self.env['product.product'].create({
            'name': 'product_c',
            'uom_id': self.env.ref('uom.product_uom_dozen').id,
            'lst_price': 120.0,
            'standard_price': 100.0,
            'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((self.tax_sale_a + self.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((self.tax_purchase_a + self.tax_purchase_b).ids)],
            'is_storable': True
        })
        kit_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_final_prod.product_tmpl_id.id,
            'product_uom_id': kit_final_prod.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
        })
        # bom line of product_c is expressed in unit to check the uom conversion (24 unit should give the same result as 2 dozens)
        kit_bom.bom_line_ids = [
            Command.create({
                'product_id': self.product_b.id,
                'product_qty': 4,
            }),
            Command.create({
                'product_id': product_c.id,
                'product_qty': 24,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id
            }),
        ]

        self.env['product.supplierinfo'].create({
            'product_id': self.product_b.id,
            'partner_id': self.partner_a.id,
            'price': 160,
        })
        self.env['product.supplierinfo'].create({
            'product_id': product_c.id,
            'partner_id': self.partner_a.id,
            'price': 100,
        })
        self.product_b.standard_price = 10
        (kit_final_prod + self.product_b).categ_id.write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_b.id,
            'order_line': [Command.create({
                'price_unit': 900,
                'product_id': kit_final_prod.id,
                'route_ids': [Command.link(self.dropship_route.id)],
                'product_uom_qty': 2.0,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order._get_purchase_orders()[0]
        purchase_order.button_confirm()
        dropship_transfer = purchase_order.picking_ids[0]
        dropship_transfer.button_validate()

        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Each product_a should cost:
        # 4x product_b = 160 * 4 = 640 +
        # 2x product_c = 100 * 2 = 200
        #                        = 840

        # Since the kit is dropshipped, the expense should be recorded in the PO directly, as it never enter the stock.
        self.assertRecordValues(bill.line_ids.sorted('balance'), [
            {'name': False,          'account_name': 'Account Payable',   'debit': 0.0,      'credit': 2184.0},
            {'name': '15%',          'account_name': 'Tax Paid',          'debit': 252.0,    'credit': 0.0},
            {'name': '15% (copy)',   'account_name': 'Tax Paid',          'debit': 252.0,    'credit': 0.0},
            {'name': 'product_c',    'account_name': 'Expenses',          'debit': 400.0,    'credit': 0.0},
            {'name': 'product_b',    'account_name': 'Expenses',          'debit': 1280.0,   'credit': 0.0},
        ])

        self.assertRecordValues(invoice.line_ids.sorted('balance'), [
            {'name': 'product_a',                                            'account_name': 'Product Sales',               'debit': 0.0,      'credit': 1800.0},
            {'name': '15% (copy)',                                           'account_name': 'Tax Received',                'debit': 0.0,      'credit': 270.0},
            {'name': f'{sale_order.name} - {invoice.name} installment #1',   'account_name': 'Account Receivable (copy)',   'debit': 621.0,    'credit': 0.0},
            {'name': f'{sale_order.name} - {invoice.name} installment #2',   'account_name': 'Account Receivable (copy)',   'debit': 1449.0,   'credit': 0.0},
        ])

    def test_dropship_kit_bom_updates_component_standard_price(self):
        """
        Ensure that a dropship sale order for a kit correctly updates
        the component product's standard_price from the supplier price after validating
        the dropship transfer.
        """
        kit_final_prod = self.product_a
        avco_products = avco_product, avco_product_2 = self.env['product.product'].create([{
            'name': f'avco product{i}',
            'is_storable': True,
            'categ_id': self.categ_avco_auto.id,
        } for i in range(2)])
        kit_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_final_prod.product_tmpl_id.id,
            'product_uom_id': kit_final_prod.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
        })
        kit_bom.bom_line_ids = [
            Command.create({
                'product_id': product.id,
                'product_qty': 2,
            }) for product in avco_products
        ]
        self.env['product.supplierinfo'].create([{
            'product_id': product.id,
            'partner_id': self.partner_a.id,
            'price': 100,
        } for product in avco_products])

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_b.id,
            'order_line': [Command.create({
                'price_unit': 900,
                'product_id': kit_final_prod.id,
                'route_ids': [Command.link(self.dropship_route.id)],
                'product_uom_qty': 2.0,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order._get_purchase_orders()[0]
        purchase_order.button_confirm()
        dropship_transfer = purchase_order.picking_ids[0]
        dropship_transfer.button_validate()

        self.assertEqual(avco_product.standard_price, 100)
        self.assertEqual(avco_product_2.standard_price, 100)
