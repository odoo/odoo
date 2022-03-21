# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSaleDropshippingFlows(TestMrpSubcontractingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
            'seller_ids': [(0, 0, {'partner_id': seller.id})],
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
