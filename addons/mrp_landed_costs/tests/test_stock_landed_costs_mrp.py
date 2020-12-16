# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestStockLandedCostsMrp(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestStockLandedCostsMrp, cls).setUpClass()
        # References
        cls.supplier_id = cls.env['res.partner'].create({'name': 'My Test Supplier'}).id
        cls.customer_id = cls.env['res.partner'].create({'name': 'My Test Customer'}).id
        cls.picking_type_in_id = cls.env.ref('stock.picking_type_in')
        cls.picking_type_out_id = cls.env.ref('stock.picking_type_out')
        cls.supplier_location_id = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location_id = cls.company_data['default_warehouse'].lot_stock_id
        cls.customer_location_id = cls.env.ref('stock.stock_location_customers')
        cls.categ_all = cls.env.ref('product.product_category_all')
        # Create product refrigerator & oven
        cls.product_component1 = cls.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'standard_price': 1.0,
            'categ_id': cls.categ_all.id
        })
        cls.product_component2 = cls.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'standard_price': 2.0,
            'categ_id': cls.categ_all.id
        })
        cls.product_refrigerator = cls.env['product.product'].create({
            'name': 'Refrigerator',
            'type': 'product',
            'categ_id': cls.categ_all.id
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.bom_refri = cls.env['mrp.bom'].create({
            'product_id': cls.product_refrigerator.id,
            'product_tmpl_id': cls.product_refrigerator.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
        })
        cls.bom_refri_line1 = cls.env['mrp.bom.line'].create({
            'bom_id': cls.bom_refri.id,
            'product_id': cls.product_component1.id,
            'product_qty': 3,
        })
        cls.bom_refri_line2 = cls.env['mrp.bom.line'].create({
            'bom_id': cls.bom_refri.id,
            'product_id': cls.product_component2.id,
            'product_qty': 1,
        })
        # Warehouses
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'})

        cls.product_refrigerator.categ_id.property_cost_method = 'fifo'
        cls.product_refrigerator.categ_id.property_valuation = 'real_time'
        cls.product_refrigerator.categ_id.property_stock_account_input_categ_id = cls.company_data['default_account_stock_in']
        cls.product_refrigerator.categ_id.property_stock_account_output_categ_id = cls.company_data['default_account_stock_out']

        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        cls.landed_cost = cls.env['product.product'].create({
            'name': 'Landed Cost',
            'type': 'service',
        })
        cls.allow_user = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': "Adviser",
            'login': "fm",
            'email': "accountmanager@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('account.group_account_manager').id, cls.env.ref('mrp.group_mrp_user').id, cls.env.ref('stock.group_stock_manager').id])]
        })

    def test_landed_cost_on_mrp(self):
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'line_ids': [(0, 0, {
                'product_id': self.product_component1.id,
                'product_uom_id': self.product_component1.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            }), (0, 0, {
                'product_id': self.product_component2.id,
                'product_uom_id': self.product_component2.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        man_order_form = Form(self.env['mrp.production'].with_user(self.allow_user))
        man_order_form.product_id = self.product_refrigerator
        man_order_form.bom_id = self.bom_refri
        man_order_form.product_qty = 2.0
        man_order = man_order_form.save()

        self.assertEqual(man_order.state, 'draft', "Production order should be in draft state.")
        man_order.action_confirm()
        self.assertEqual(man_order.state, 'confirmed', "Production order should be in confirmed state.")

        # check production move
        production_move = man_order.move_finished_ids
        self.assertEqual(production_move.product_id, self.product_refrigerator)

        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_component1)
        self.assertEqual(first_move.product_qty, 6.0)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_component2)
        self.assertEqual(first_move.product_qty, 2.0)

        # produce product
        mo_form = Form(man_order.with_user(self.allow_user))
        mo_form.qty_producing = 2
        man_order = mo_form.save()


        man_order.button_mark_done()

        landed_cost = Form(self.env['stock.landed.cost'].with_user(self.allow_user)).save()
        landed_cost.target_model = 'manufacturing'

        self.assertTrue(man_order.id in landed_cost.allowed_mrp_production_ids.ids)
        landed_cost.mrp_production_ids = [(6, 0, [man_order.id])]
        landed_cost.cost_lines = [(0, 0, {'product_id': self.landed_cost.id, 'price_unit': 5.0, 'split_method': 'equal'})]

        landed_cost.button_validate()

        self.assertEqual(landed_cost.state, 'done')
        self.assertTrue(landed_cost.account_move_id)
        # Link to one layer of product_refrigerator
        self.assertEqual(len(landed_cost.stock_valuation_layer_ids), 1)
        self.assertEqual(landed_cost.stock_valuation_layer_ids.product_id, self.product_refrigerator)
        self.assertEqual(landed_cost.stock_valuation_layer_ids.value, 5.0)
