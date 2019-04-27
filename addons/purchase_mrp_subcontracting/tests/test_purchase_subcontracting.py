# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestPurchaseSubcontractingFlows(TransactionCase):
    def setUp(self):
        super(TestPurchaseSubcontractingFlows, self).setUp()

        # 1. Create a BOM of subcontracting type
        self.comp1 = self.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.comp2 = self.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.finished_product = self.env['product.product'].create({
            'name': 'finished',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.product_tmpl_id = self.finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp1
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp2
            bom_line.product_qty = 1
        self.bom_finished_product = bom_form.save()

        # 2: Create a subcontracting partner
        company_partner = self.env['res.partner'].create({'name': 'main_partner', 'is_company': True})
        self.subcontractor_partner1 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'type': 'subcontractor',
            'parent_id': company_partner.id,
        })

        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def test_purchase_1(self):
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'

        # IN 10@10 comp1 10@20 comp2
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.user.company_id.subcontracting_location_id.id,
            'product_id': self.comp1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 20.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.user.company_id.subcontracting_location_id.id,
            'product_id': self.comp2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        po1 = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [
                (0, 0, {
                    'name': self.finished_product.name,
                    'product_id': self.finished_product.id,
                    'product_qty': 1,
                    'product_uom': self.finished_product.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_finished_product.id)])
        self.assertEqual(len(mo), 1)

        move1 = picking1.move_lines[0]
        move1.quantity_done = 1
        picking1.button_validate()
        self.assertEqual(mo.move_finished_ids.value, 60)
        # waiting forward port of 67ea26460ff27d6a
        # self.assertEqual(mo.move_finished_ids.product_id.stock_value, 60)

