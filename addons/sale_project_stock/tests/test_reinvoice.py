# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon


class TestReInvoice(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id,
            'partner_shipping_id': cls.partner.id,
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Project',
            'reinvoiced_sale_order_id': cls.sale_order.id,
        })
        cls.picking_out = cls.PickingObj.create({
            'picking_type_id': cls.picking_type_out,
            'location_id': cls.stock_location,
            'location_dest_id': cls.customer_location,
            'project_id': cls.project.id,
        })
        cls.picking_out.picking_type_id.analytic_costs = True
        cls.reinvoicable_product_at_cost, cls.reinvoicable_product_sales_price = cls.env['product.product'].create([
            {
                'name': 'product_order_cost',
                'standard_price': 100.0,
                'expense_policy': 'cost',
            },
            {
                'name': 'product_order_cost',
                'list_price': 500.0,
                'expense_policy': 'sales_price',
            },
        ])
        cls.sale_order.action_confirm()

    def test_picking_reinvoicing(self):
        move_values = {
            'name': 'Move',
            'product_uom': self.uom_unit.id,
            'picking_id': self.picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        }
        self.MoveObj.create([
            {
                **move_values,
                'product_id': self.reinvoicable_product_at_cost.id,
                'product_uom_qty': 3,
            },
            {
                **move_values,
                'product_id': self.reinvoicable_product_sales_price.id,
                'product_uom_qty': 5,
            },
        ])
        self.picking_out.with_user(self.user_stock_user).action_confirm()
        self.picking_out.with_user(self.user_stock_user).button_validate()

        self.assertEqual(len(self.sale_order.order_line), 2, 'There should be 2 lines on the SO')
        new_sale_order_line1 = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.reinvoicable_product_at_cost)
        self.assertTrue(new_sale_order_line1, 'A new sale line should have been created with the reinvoicable product at cost')
        self.assertEqual(
            (new_sale_order_line1.price_unit, new_sale_order_line1.qty_delivered, new_sale_order_line1.product_uom_qty, new_sale_order_line1.qty_invoiced),
            (self.reinvoicable_product_at_cost.standard_price, 3, 3, 0),
            'Sale line is wrong after confirming the picking',
        )
        self.assertEqual(new_sale_order_line1.qty_delivered_method, 'stock_move', 'Delivered quantity of SO line should be computed by stock move')

        new_sale_order_line2 = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.reinvoicable_product_sales_price)
        self.assertTrue(new_sale_order_line2, 'A new sale line should have been created with the reinvoicable product at sales price')
        self.assertEqual(
            (new_sale_order_line2.price_unit, new_sale_order_line2.qty_delivered, new_sale_order_line2.product_uom_qty, new_sale_order_line2.qty_invoiced),
            (self.reinvoicable_product_sales_price.list_price, 5, 5, 0),
            'Sale line is wrong after confirming the picking',
        )
        self.assertEqual(new_sale_order_line2.qty_delivered_method, 'stock_move', 'Delivered quantity of SO line should be computed by stock move')
