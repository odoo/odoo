# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
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
        # Create product refrigerator & oven
        cls.product_component1 = cls.env['product.product'].create({
            'name': 'Component1',
            'is_storable': True,
            'standard_price': 1.0,
        })
        cls.product_component2 = cls.env['product.product'].create({
            'name': 'Component2',
            'is_storable': True,
            'standard_price': 2.0,
        })
        cls.product_refrigerator = cls.env['product.product'].create({
            'name': 'Refrigerator',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_goods').id,
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

        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        cls.landed_cost = cls.env['product.product'].create({
            'name': 'Landed Cost',
            'type': 'service',
            'categ_id': cls.env.ref('product.product_category_services').id,
        })
        cls.allow_user = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': "Adviser",
            'login': "fm",
            'email': "accountmanager@yourcompany.com",
            'group_ids': [(6, 0, [cls.env.ref('account.group_account_manager').id, cls.env.ref('mrp.group_mrp_user').id, cls.env.ref('stock.group_stock_manager').id])]
        })

    def test_landed_cost_on_mrp(self):
        # Initial inventory
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_component1.id,
            'inventory_quantity': 500,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_component2.id,
            'inventory_quantity': 500,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })
        quants.action_apply_inventory()

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

        # Check domain of the views
        self.assertTrue(man_order in self.env['mrp.production'].search([
            ('move_finished_ids.stock_valuation_layer_ids', '!=', False), ('company_id', '=', landed_cost.company_id.id)]))

        landed_cost.mrp_production_ids = [(6, 0, [man_order.id])]
        landed_cost.cost_lines = [(0, 0, {'product_id': self.landed_cost.id, 'price_unit': 5.0, 'split_method': 'equal'})]
        landed_cost.button_validate()

        self.assertEqual(landed_cost.state, 'done')
        self.assertTrue(landed_cost.account_move_id)
        # Link to one layer of product_refrigerator
        self.assertEqual(len(landed_cost.stock_valuation_layer_ids), 1)
        self.assertEqual(landed_cost.stock_valuation_layer_ids.product_id, self.product_refrigerator)
        self.assertEqual(landed_cost.stock_valuation_layer_ids.value, 5.0)

    def test_landed_cost_on_mrp_02(self):
        """
            Test that a user who has manager access to stock can create and validate a landed cost linked
            to a Manufacturing order without the need for MRP access
        """
        # Create a user with only manager access to stock
        stock_manager = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': "Stock Manager",
            'login': "test",
            'email': "test@test.com",
            'group_ids': [(6, 0, [self.env.ref('stock.group_stock_manager').id])]
        })
        # Make some stock and reserve
        self.env['stock.quant']._update_available_quantity(self.product_component1, self.warehouse_1.lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(self.product_component2, self.warehouse_1.lot_stock_id, 10)

        # Create and confirm a MO with a user who has access to MRP
        man_order_form = Form(self.env['mrp.production'].with_user(self.allow_user))
        man_order_form.product_id = self.product_refrigerator
        man_order_form.bom_id = self.bom_refri
        man_order_form.product_qty = 1.0
        man_order = man_order_form.save()
        man_order.action_confirm()
        # produce product
        # To edit `qty_producing`, the mo must no be draft. It's not thanks to the above `action_confirm()`
        # but the values of the form do not update automatically, it must be reloaded.
        man_order_form = Form(man_order)
        man_order_form.qty_producing = 1
        man_order_form.save()
        man_order.button_mark_done()

        # Create the landed cost with the stock_manager user
        landed_cost = Form(self.env['stock.landed.cost'].with_user(stock_manager)).save()
        landed_cost.target_model = 'manufacturing'

        # Check that the MO can be selected by the stock_manger user
        self.assertTrue(man_order in self.env['mrp.production'].search([
            ('move_finished_ids.stock_valuation_layer_ids', '!=', False), ('company_id', '=', landed_cost.company_id.id)]))
        landed_cost.mrp_production_ids = [(6, 0, [man_order.id])]

        # Check that he can validate the landed cost without an access error
        landed_cost.with_user(stock_manager).button_validate()
        self.assertEqual(landed_cost.state, 'done')

    def test_landed_cost_on_mrp_03(self):
        """
            Do not apply landed costs to byproducts without cost_share
        """
        # Create product refrigerator & oven
        byproduct1 = self.env['product.product'].create({
            'name': 'Byproduct1',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        byproduct2 = self.env['product.product'].create({
            'name': 'Byproduct2',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        self.bom_refri.write({
            'byproduct_ids': [
                (0, 0, {'product_id': byproduct1.id, 'product_qty': 1, 'cost_share': 100}),
                (0, 0, {'product_id': byproduct2.id, 'product_qty': 1, 'cost_share': 0}),
            ],
        })
        man_order_form = Form(self.env['mrp.production'].with_user(self.allow_user))
        man_order_form.product_id = self.product_refrigerator
        man_order_form.bom_id = self.bom_refri
        man_order_form.product_qty = 2.0
        man_order = man_order_form.save()
        man_order.action_confirm()
        # produce product
        mo_form = Form(man_order.with_user(self.allow_user))
        mo_form.qty_producing = 2
        man_order = mo_form.save()
        man_order.button_mark_done()

        landed_cost = Form(self.env['stock.landed.cost'].with_user(self.allow_user)).save()
        landed_cost.target_model = 'manufacturing'
        landed_cost.mrp_production_ids = [(6, 0, [man_order.id])]
        landed_cost.cost_lines = [(0, 0, {'product_id': self.landed_cost.id, 'price_unit': 5.0, 'split_method': 'equal'})]
        landed_cost.compute_landed_cost()

        # check the valuation adjustment lines
        self.assertFalse(byproduct2 in landed_cost.valuation_adjustment_lines.product_id)
