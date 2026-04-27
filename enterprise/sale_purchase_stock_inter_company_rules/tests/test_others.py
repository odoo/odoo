# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, tagged
from .common import TestInterCompanyRulesCommonStock


@tagged('post_install', '-at_install')
class TestInterCompanyOthersWithStock(TestInterCompanyRulesCommonStock):

    def test_return_purchase_on_inter_company(self):
        """
        Check that returning the reciept of an inter-company transit
        updates the received quantity correctly.
        """
        super_product = self.env['product.product'].create({
            'name': 'Super Product',
            'is_storable': True,
            'company_id': False,
        })
        purchase_order = Form(self.env['purchase.order'].with_company(self.company_a))
        purchase_order.partner_id = self.company_b.partner_id
        purchase_order.company_id = self.company_a
        purchase_order = purchase_order.save()

        with Form(purchase_order.with_company(self.company_b)) as po:
            with po.order_line.new() as line:
                line.product_id = super_product
                line.product_qty = 10.0

        # Confirm Purchase order
        purchase_order.with_company(self.company_a).button_confirm()
        receipt = purchase_order.picking_ids
        self.assertRecordValues(receipt.move_ids, [{
            'product_id': super_product.id,
            'product_uom_qty': 10.0,
        }])
        # validate the receipt
        receipt.move_ids.quantity = 10.0
        receipt.move_ids.picked = True
        receipt.with_company(self.company_a).button_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(purchase_order.order_line.qty_received, 10.0)
        # return the units to the inter company transit location
        self.env.user.groups_id |= self.env.ref('stock.group_stock_multi_locations')
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_company(self.company_a).with_context(active_ids=receipt.ids, active_id=receipt.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({'quantity': 10.0})
        res = return_wiz.action_create_returns()
        pick_return = self.env['stock.picking'].browse(res['res_id'])
        self.assertEqual(pick_return.location_dest_id, self.env.ref('stock.stock_location_inter_company'))
        pick_return.move_ids.quantity = 10.0
        pick_return.move_ids.picked = True
        pick_return.with_company(self.company_a).button_validate()
        self.assertEqual(pick_return.state, 'done')
        self.assertEqual(purchase_order.order_line.qty_received, 0.0)

    def test_inter_company_kit_delivery_delivery_reception_1(self):
        """ Upon completion of a delivery for a kit product to another internal company, ensure
        that the corresponding SOL reflects the qty has been delivered and received on each
        company's related order line record.

        (self.env.company == self.company_a)
        """
        if 'mrp.bom' not in self.env:
            self.skipTest('This test requires the following modules: mrp')

        self.env.user._get_default_warehouse_id().delivery_steps = 'pick_ship'
        (self.company_b | self.company_a).update({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
        })
        self.product.write({'is_storable': True, 'name': 'kit product'})
        kit_product = self.product
        self.env['mrp.bom'].create({
            'product_id': kit_product.id,
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'company_id': False,
            'bom_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'product_qty': 2,
            })],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.company_b.partner_id.id,
            'order_line': [Command.create({
                'product_id': kit_product.id,
                'product_uom_qty': 2,
            })],
        })
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        delivery.move_ids.quantity = 4
        delivery.button_validate()
        delivery = sale_order.picking_ids.filtered(lambda p: p.state != 'done')
        delivery.button_validate()

        purchase_order = self.env['purchase.order'].with_company(self.company_b).search([
            ('auto_sale_order_id', '=', sale_order.id),
        ])
        purchase_order.with_company(self.company_b).button_confirm()
        receipt = purchase_order.picking_ids
        receipt.with_company(self.company_b).move_ids.quantity = 4
        receipt.with_company(self.company_b).button_validate()
        self.assertRecordValues(
            sale_order.order_line,
            [{'qty_delivered': 2.0, 'product_id': kit_product.id}]
        )
        self.assertRecordValues(
            purchase_order.order_line,
            [{'qty_received': 2.0, 'product_id': kit_product.id}]
        )

    def test_inter_company_kit_delivery_delivery_reception_2(self):
        """ In an intercompany sale/purchase of a kit product where each company has a different BoM for that product,
        the purchase & sale lines should end up with accurate received/delivered (resp.) quantity values.
        """
        if 'mrp.bom' not in self.env:
            self.skipTest('This test requires the following modules: mrp')

        self.env.user._get_default_warehouse_id().delivery_steps = 'pick_ship'
        (self.company_b | self.company_a).update({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
        })
        self.product.write({'is_storable': True, 'name': 'kit product'})
        kit_product = self.product
        components = self.env['product.product'].create([{'name': f'comp {i}', 'is_storable': True} for i in range(3)])
        self.env['mrp.bom'].create({
            'product_id': kit_product.id,
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'company_id': False,
            'bom_line_ids': [
                Command.create({'product_id': components[0].id,'product_qty': 2}),
                Command.create({'product_id': components[1].id,'product_qty': 3})
            ],
        })
        self.env['mrp.bom'].create({
            'product_id': kit_product.id,
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'company_id': False,
            'bom_line_ids': [
                Command.create({'product_id': components[1].id,'product_qty': 4}),
                Command.create({'product_id': components[2].id,'product_qty': 5})
            ],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.company_b.partner_id.id,
            'order_line': [Command.create({
                'product_id': kit_product.id,
                'product_uom_qty': 2,
            })],
        })
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        for move in delivery.move_ids:
            move.quantity = move.product_uom_qty
        delivery.button_validate()
        delivery = sale_order.picking_ids.filtered(lambda p: p.state != 'done')
        delivery.button_validate()

        purchase_order = self.env['purchase.order'].with_company(self.company_b).search([
            ('auto_sale_order_id', '=', sale_order.id),
        ])
        purchase_order.with_company(self.company_b).button_confirm()
        receipt = purchase_order.picking_ids
        for move in receipt.move_ids:
            move.quantity = move.product_uom_qty
        receipt.with_company(self.company_b).button_validate()
        self.assertRecordValues(
            sale_order.order_line,
            [{'qty_delivered': 2.0, 'product_id': kit_product.id}]
        )
        self.assertRecordValues(
            purchase_order.order_line,
            [{'qty_received': 2.0, 'product_id': kit_product.id}]
        )
