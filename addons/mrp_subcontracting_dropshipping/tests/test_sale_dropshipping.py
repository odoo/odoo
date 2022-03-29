# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSaleDropshippingFlows(TestMrpSubcontractingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier = cls.env["res.partner"].create({"name": "Supplier"})
        cls.customer = cls.env["res.partner"].create({"name": "Customer"})
        cls.dropship_route = cls.env.ref('stock_dropshipping.route_drop_shipping')

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
        picking = sale_order.picking_ids.filtered(lambda p: p.partner_id == partners[0])
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

        # Deliver the third one
        picking = sale_order.picking_ids.filtered(lambda p: p.partner_id == partners[2])
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
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
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
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
            wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
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
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
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
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
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
