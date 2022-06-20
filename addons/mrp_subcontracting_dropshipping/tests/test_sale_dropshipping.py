from odoo.tests import Form
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSaleDropshippingFlows(TestMrpSubcontractingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier = cls.env["res.partner"].create({"name": "Supplier"})
        cls.customer = cls.env["res.partner"].create({"name": "Customer"})
        cls.dropship_route = cls.env.ref('stock_dropshipping.route_drop_shipping')
    
    def test_dropship_with_different_uom(self):
        """This test checks the flow when we add a sale order
        for a product with a bom which contains two components
        with two differents UoM, save it, and then
        modify the quantity. This test is here instead of
        stock_dropshipping, in order to be able to use
        mrp.bom, which is not a dependency of stock_dropshipping.
        """

        location = self.env.ref('stock.stock_location_stock')

        # Create a product
        test_product = self.env['product.template'].create({"name": "Product"})

        # Create a component with UoM Liters with dropshipping route
        component_liter = self.env['product.template'].create({
            "name": "component liter",
            "route_ids": [(6, 0, [self.dropship_route.id])],
            "seller_ids": [(0, 0, {
                'delay': 1,
                'name': self.supplier.id,
                'min_qty': 1.0
            })],
            "uom_id": 11,
            "uom_po_id": 11,
        })

        # Create an other component with UoM Units without dropshipping route
        component_unit = self.env['product.template'].create({
            "name": "component liter",
            "type": "product",
            "uom_id": 1,
            "uom_po_id": 1,
        })

        self.env['stock.quant']._update_available_quantity(component_unit.product_variant_id, location, 100)

        # Create a BoM for the product with the two components
        self.env['mrp.bom'].create({
            "product_tmpl_id": test_product.id,
            "product_id": False,
            "product_qty": 1,
            "type": "phantom",
            "bom_line_ids": [
                [0, 0, {"product_id": component_liter.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_unit.product_variant_id.id, "product_qty": 1}],
            ]
        })

        # Create a sales order with a line of 1 test_product
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_2')
        so_form.payment_term_id = self.env.ref('account.account_payment_term_end_following_month')
        with so_form.order_line.new() as line:
            line.product_id = test_product.product_variant_id
            line.product_uom_qty = 1
            line.price_unit = 1.00
        sale_order = so_form.save()
        sale_order.action_confirm()

        # Modify the quantity on sale order line
        sale_order.write({'order_line': [[1, sale_order.order_line.id, {'product_uom_qty': 2.00}]]})

        self.assertEqual(sale_order.order_line.product_uom_qty, 2)

    def test_dropship_with_different_suppliers(self):
        """
        Suppose a kit with 3 components supplied by 3 vendors
        When dropshipping this kit, if 2 components are delivered and if the last
        picking is cancelled, we should consider the kit as fully delivered.
        """
        partners = self.env['res.partner'].create([{'name': 'Vendor %s' % i} for i in range(4)])
        compo01, compo02, compo03, kit = self.env['product.product'].create([{
            'name': name,
            'type': 'consu',
            'route_ids': [(6, 0, [self.dropship_route.id])],
            'seller_ids': [(0, 0, {'name': seller.id})],
        } for name, seller in zip(['Compo01', 'Compo02', 'Compo03', 'Kit'], partners)])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1}),
                (0, 0, {'product_id': compo03.id, 'product_qty': 1}),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': kit.name, 'product_id': kit.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

        purchase_orders = self.env['purchase.order'].search([('partner_id', 'in', partners.ids)])
        purchase_orders.button_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

        # Deliver the first one
        picking = sale_order.picking_ids[0]
        action = picking.button_validate()
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

        # Deliver the third one
        picking = sale_order.picking_ids[2]
        action = picking.button_validate()
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

        # Cancel the second one
        sale_order.picking_ids[1].action_cancel()
        self.assertEqual(sale_order.order_line.qty_delivered, 1)

    def test_return_kit_and_delivered_qty(self):
        """
        Sell a kit thanks to the dropshipping route, return it then deliver it again
        The delivered quantity should be correctly computed
        """
        compo, kit = self.env['product.product'].create([{
            'name': n,
            'type': 'consu',
            'route_ids': [(6, 0, [self.dropship_route.id])],
            'seller_ids': [(0, 0, {'name': self.supplier.id})],
        } for n in ['Compo', 'Kit']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 1}),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': kit.name, 'product_id': kit.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        self.env['purchase.order'].search([], order='id desc', limit=1).button_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)

        picking = sale_order.picking_ids
        action = picking.button_validate()
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 1.0)

        for case in ['return', 'deliver again']:
            delivered_before_case = 1.0 if case == 'return' else 0.0
            delivered_after_case = 0.0 if case == 'return' else 1.0
            return_form = Form(self.env['stock.return.picking'].with_context(active_ids=[picking.id], active_id=picking.id, active_model='stock.picking'))
            return_wizard = return_form.save()
            action = return_wizard.create_returns()
            picking = self.env['stock.picking'].browse(action['res_id'])
            self.assertEqual(sale_order.order_line.qty_delivered, delivered_before_case, "Incorrect delivered qty for case '%s'" % case)

            action = picking.button_validate()
            wizard = self.env[action['res_model']].browse(action['res_id'])
            wizard.process()
            self.assertEqual(sale_order.order_line.qty_delivered, delivered_after_case, "Incorrect delivered qty for case '%s'" % case)

    def test_partial_return_kit_and_delivered_qty(self):
        """
        Suppose a kit with 4x the same dropshipped component
        Suppose a complex delivery process:
            - Deliver 2 (with backorder)
            - Return 2
            - Deliver 1 (with backorder)
            - Deliver 1 (process "done")
            - Deliver 1 (from the return)
            - Deliver 1 (from the return)
        The test checks the all-or-nothing policy of the delivered quantity
        This quantity should be 1.0 after the last delivery
        """
        compo, kit = self.env['product.product'].create([{
            'name': n,
            'type': 'consu',
            'route_ids': [(6, 0, [self.dropship_route.id])],
            'seller_ids': [(0, 0, {'name': self.supplier.id})],
        } for n in ['Compo', 'Kit']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 4}),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': kit.name, 'product_id': kit.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        self.env['purchase.order'].search([], order='id desc', limit=1).button_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 0/4")

        picking01 = sale_order.picking_ids
        picking01.move_lines.quantity_done = 2
        action = picking01.button_validate()
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 2/4")

        # Create a return of picking01 (with both components)
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=picking01.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.write({'quantity': 2.0})
        res = wizard.create_returns()
        return01 = self.env['stock.picking'].browse(res['res_id'])

        return01.move_lines.quantity_done = 2
        return01.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 0/4")

        picking02 = picking01.backorder_ids
        picking02.move_lines.quantity_done = 1
        action = picking02.button_validate()
        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 1/4")

        picking03 = picking02.backorder_ids
        picking03.move_lines.quantity_done = 1
        picking03.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 2/4")

        # Create a return of return01 (with 1 component)
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=return01.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.write({'quantity': 1.0})
        res = wizard.create_returns()
        picking04 = self.env['stock.picking'].browse(res['res_id'])

        picking04.move_lines.quantity_done = 1
        picking04.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0, "Delivered components: 3/4")

        # Create a second return of return01 (with 1 component, the last one)
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=return01.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.write({'quantity': 1.0})
        res = wizard.create_returns()
        picking04 = self.env['stock.picking'].browse(res['res_id'])

        picking04.move_lines.quantity_done = 1
        picking04.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 1, "Delivered components: 4/4")

    def test_cancelled_picking_and_delivered_qty(self):
        """
        The delivered quantity should be zero if all SM are cancelled
        """
        compo, kit = self.env['product.product'].create([{
            'name': n,
            'type': 'consu',
            'route_ids': [(6, 0, [self.dropship_route.id])],
            'seller_ids': [(0, 0, {'name': self.supplier.id})],
        } for n in ['Compo', 'Kit']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 1}),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': kit.name, 'product_id': kit.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        self.env['purchase.order'].search([], order='id desc', limit=1).button_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)

        sale_order.picking_ids.action_cancel()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)

    def test_sale_kit_with_dropshipped_component(self):
        """
        The test checks the delivered quantity of a kit when one of the
        components is dropshipped
        """
        compo01, compo02, kit = self.env['product.product'].create([{
            'name': n,
            'type': 'consu',
        } for n in ['compo01', 'compo02', 'super kit']])

        compo02.write({
            'route_ids': [(6, 0, [self.dropship_route.id])],
            'seller_ids': [(0, 0, {'name': self.supplier.id})],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1}),
            ],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': kit.name, 'product_id': kit.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        self.env['purchase.order'].search([], order='id desc', limit=1).button_confirm()

        sale_order.picking_ids.move_lines.quantity_done = 1
        sale_order.picking_ids[0].button_validate()
        sale_order.picking_ids[1].button_validate()

        self.assertEqual(sale_order.order_line.qty_delivered, 1.0)
