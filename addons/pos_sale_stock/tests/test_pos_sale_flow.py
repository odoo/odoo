# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from odoo.addons.pos_stock.tests.test_frontend import TestPosStockHttpCommon
from odoo.addons.pos_sale.tests.test_pos_sale_flow import TestPoSSale


class TestPoSSaleStock(TestPosStockHttpCommon, TestPoSSale):

    def test_settle_order_with_kit(self):
        if not self.env["ir.module.module"].search([("name", "=", "mrp"), ("state", "=", "installed")]):
            self.skipTest("mrp module is required for this test")

        self.env.user.group_ids |= self.env.ref('mrp.group_mrp_user')
        self.kit = self.env['product.product'].create({
            'name': 'Pizza Chicken',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Chicken',
            'is_storable': True,
            'available_in_pos': True,
            'uom_id': self.env.ref('uom.product_uom_gram').id,
            'lst_price': 10.0,
        })
        self.location = self.env['stock.location'].sudo().create({
            'name': 'Test location',
            'usage': 'internal',
        }).sudo(False)

        self.env['stock.quant']._update_available_quantity(self.component_a, self.location, 100000)

        bom_product_form = Form(self.env['mrp.bom'].sudo())
        if self.env.user._has_group('product.group_product_variant'):
            bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 300.0
        self.bom_a = bom_product_form.save()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.kit.id,
                'name': self.kit.name,
                'product_uom_qty': 10,
                'price_unit': self.kit.lst_price,
            })],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity = 300
        picking.move_ids.picked = True
        Form.from_action(self.env, picking.button_validate()).save().process()

        self.assertEqual(sale_order.order_line.qty_delivered, 1)

        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_user').id),
                (4, self.env.ref('sales_team.group_sale_salesman_all_leads').id),
                (4, self.env.ref('account.group_account_user').id),
                (4, self.env.ref('base.group_system').id),  # FIXME refacto
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleOrder', login="pos_user")

        # assert that sales order qty are correctly updated
        self.assertEqual(sale_order.order_line.qty_delivered, 3)
        self.assertEqual(sale_order.picking_ids[0].move_ids.product_qty, 2100)  # 7 left to deliver => 300 * 7 = 2100
        self.assertEqual(sale_order.picking_ids[0].move_ids.quantity, 0)
        self.assertEqual(sale_order.picking_ids[1].move_ids.product_qty, 300)
        self.assertEqual(sale_order.picking_ids[1].move_ids.quantity, 300)  # 1 delivered => 300 * 2 = 600

    def test_settle_order_with_different_product(self):
        """This test create an order and settle it in the PoS. But only one of the product is delivered.
            And we need to make sure the quantity are correctly updated on the sale order.
        """
        # create 2 products
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        # create a sale order with 2 lines
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'price_unit': product_b.lst_price,
            }), (0, 0, {
                # Add this line to test that it should not cause any issue when settling this order.
                'name': 'section line',
                'display_type': 'line_section',
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)

        self.main_pos_config.open_ui()
        self.main_pos_config.current_session_id.update_stock_at_closing = True
        self.start_pos_tour('PosSettleOrder2', login="accountman")

        sale_order = self.env['sale.order'].browse(sale_order.id)
        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)
        orderline_product_a = sale_order.order_line.filtered(lambda l: l.product_id.id == product_a.id)
        orderline_product_b = sale_order.order_line.filtered(lambda l: l.product_id.id == product_b.id)
        # nothing to deliver for product a because already handled in pos.
        self.assertEqual(orderline_product_a.move_ids.product_uom_qty, 0)
        # 1 item to deliver for product b.
        self.assertEqual(orderline_product_b.move_ids.product_uom_qty, 1)

    def test_settle_order_unreserve_order_lines(self):
        # create a product category that use the closest location for the removal strategy
        self.removal_strategy = self.env['product.removal'].search([('method', '=', 'closest')], limit=1)
        self.product_category = self.env['product.category'].create({
            'name': 'Product Category',
            'removal_strategy_id': self.removal_strategy.id,
        })

        self.product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': self.product_category.id,
        })

        # create 2 stock location Shelf 1 and Shelf 2
        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.shelf_1, self.shelf_2 = self.env['stock.location'].sudo().create([{
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        }, {
            'name': 'Shelf 2',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        }]).sudo(False)

        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 2,
            'location_id': self.shelf_1.id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 5,
            'location_id': self.shelf_2.id,
        })
        quants.action_apply_inventory()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 4,
                'price_unit': self.product.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].location_id.id, self.shelf_1.id)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].location_id.id, self.shelf_2.id)

        self.main_pos_config.company_id.write({'point_of_sale_update_stock_quantities': 'real'})
        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrderRealTime', login="accountman")
        self.main_pos_config.current_session_id.close_session_from_ui()
        pos_order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(pos_order.picking_ids.move_line_ids[0].quantity, 2)
        self.assertEqual(pos_order.picking_ids.move_line_ids[0].location_id.id, self.shelf_1.id)
        self.assertEqual(pos_order.picking_ids.move_line_ids[1].quantity, 2)
        self.assertEqual(pos_order.picking_ids.move_line_ids[1].location_id.id, self.shelf_2.id)
        self.assertEqual(sale_order.order_line.move_ids.move_lines_count, 0)

    def test_settle_order_with_multistep_delivery(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """

        # get the warehouse
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.sudo().delivery_steps = 'pick_pack_ship'

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        self.env['stock.quant']._update_available_quantity(product_a, warehouse.lot_stock_id, 1)

        # create a sale order with 2 lines
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)

        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrder3', login="accountman")

        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.picking_ids.mapped('state'), ['cancel'])

    def test_import_lot_groupable_and_non_groupable(self):
        """
        Test importing a Sale Order in POS containing both groupable and non-groupable
        lot-tracked products, each with quantities exceeding available lots.
        Ensures the POS correctly handles lot selection and grouping behavior.
        """
        non_groupable_uom = self.env['uom.uom'].create({
            'name': 'Non groupable',
            'is_pos_groupable': False,
        })
        groupable_product, non_groupable_product = self.env['product.product'].create([{
            'name': name,
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'tracking': 'lot',
            'taxes_id': False,
        } for name in ('Groupable Product', 'Non Groupable Product')])
        non_groupable_product.uom_id = non_groupable_uom.id

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        non_groupable_lot, groupable_lot = self.env['stock.lot'].create([{
            'name': f'LOT {product.name}',
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for product in (non_groupable_product, groupable_product)])
        self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': lot.product_id.id,
            'inventory_quantity': 2,
            'location_id': stock_location.id,
            'lot_id': lot.id,
        } for lot in (non_groupable_lot, groupable_lot)]).action_apply_inventory()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [
                Command.create({
                    'product_id': non_groupable_product.id,
                    'name': non_groupable_product.name,
                    'product_uom_qty': 3,
                }),
                Command.create({
                    'product_id': groupable_product.id,
                    'name': groupable_product.name,
                    'product_uom_qty': 3,
                }),
            ],
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.amount_total, 60)

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_import_lot_groupable_and_non_groupable', login="accountman")

    def test_ship_later_no_default(self):
        """ Verify that when settling an order the ship later is not activated by default"""
        product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': False,
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 4,
                'price_unit': product.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.write({'ship_later': True})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosShipLaterNoDefault', login="accountman")

    def test_settle_order_with_multistep_delivery_receipt(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """
        if not self.env["ir.module.module"].search([("name", "=", "purchase"), ("state", "=", "installed")]):
            self.skipTest("purchase module is required for this test")

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        warehouse.reception_steps = 'three_steps'
        self.env.ref('stock.route_warehouse0_mto').active = True
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        route_mto = self.env.ref('stock.route_warehouse0_mto')
        route_mto.rule_ids.procure_method = 'mts_else_mto'
        self.partner_test = self.env['res.partner'].create({
            'name': 'Partner Test A',
            'street': '77 Santa Barbara Rd',
            'city': 'Pleasant Hill',
            'country_id': self.env.ref('base.nl').id,
            'zip': '1105AA',
            'state_id': False,
            'email': 'acme.corp82@example.com',
            'phone': '(603)-996-3829',
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'seller_ids': [(0, 0, {
                'partner_id': self.partner_test.id,
                'min_qty': 1.0,
                'price': 1.0,
            })],
            'route_ids': [(6, 0, [route_buy.id, route_mto.id])],
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        # We validate the purchase and receipt steps
        po = sale_order._get_purchase_orders()
        po.button_confirm()
        picking = po.picking_ids
        # validate the 3 picking in order
        picking.button_validate()
        picking = picking._get_next_transfers()
        picking.button_validate()
        picking = picking._get_next_transfers()
        picking.button_validate()

        self.main_pos_config.ship_later = True
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleOrder4', login="accountman")

        self.assertEqual(sale_order.picking_ids[0].state, 'cancel')
        self.assertEqual(sale_order.pos_order_line_ids.order_id.picking_ids.state, 'assigned')
        self.assertEqual(self.env['purchase.order.line'].search_count([('product_id', '=', product_a.id)]), 1)

    def test_settle_order_ship_later_effect_on_so(self):
        """This test create an order, settle it in the PoS and ship it later.
            We need to make sure that the quantity delivered on the original sale is updated correctly,
            And that the picking associated to the original sale order is cancelled.
        """

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'lst_price': 5.0,
        })

        partner_test = self.env['res.partner'].create({
            'name': 'Test Partner',
            'city': 'San Francisco',
            'state_id': self.env.ref('base.state_us_5').id,
            'country_id': self.env.ref('base.us').id,
            'zip': '94134',
            'street': 'Rue du burger',
        })

        sale_order_single = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })

        sale_order_multi = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'price_unit': product_b.lst_price,
            })],
        })
        self.assertEqual(sale_order_single.order_line[0].qty_delivered, 0)

        self.main_pos_config.ship_later = True
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleOrderShipLater', login="accountman")

        self.assertEqual(len(sale_order_single.picking_ids), 1)
        self.assertEqual(sale_order_single.picking_ids.state, "cancel")
        self.assertEqual(len(sale_order_single.pos_order_line_ids.order_id.picking_ids), 1)
        self.assertEqual(sale_order_single.pos_order_line_ids.order_id.picking_ids.state, "assigned")

        # The pos order is being shipped later so the qty_delivered should still be 0
        self.assertEqual(sale_order_single.order_line[0].qty_delivered, 0)

        # We validate the delivery of the order, now the qty_delivered should be 1
        pickings = sale_order_single.pos_order_line_ids.order_id.picking_ids
        pickings.move_ids.quantity = 1
        pickings.button_validate()
        self.assertEqual(sale_order_single.order_line[0].qty_delivered, 1)

        # multi line order checks
        self.assertEqual(sale_order_multi.order_line[0].qty_delivered, 0)
        self.assertEqual(sale_order_multi.order_line[1].qty_delivered, 0)

        self.assertEqual(len(sale_order_multi.picking_ids), 1)
        self.assertEqual(sale_order_multi.picking_ids.state, "cancel")
        self.assertEqual(len(sale_order_multi.pos_order_line_ids.order_id.picking_ids), 1)
        self.assertEqual(sale_order_multi.pos_order_line_ids.order_id.picking_ids.state, "assigned")

    def test_edit_invoice_with_pos_order(self):
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})

        pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': partner_1.id,
            'pricelist_id': partner_1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.desk_pad.product_variant_id.id,
                'price_unit': self.desk_pad.product_variant_id.lst_price,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [],
                'price_subtotal': self.desk_pad.product_variant_id.lst_price,
                'price_subtotal_incl': self.desk_pad.product_variant_id.lst_price,
            })],
            'amount_total': self.desk_pad.product_variant_id.lst_price,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })

        # generate an invoice for pos order
        res = pos_order.action_pos_order_invoice()
        self.assertIn('res_id', res, "Invoice should be created")
        self.assertEqual(res['res_id'], pos_order.account_move.id)

        invoice = pos_order.account_move
        self.assertEqual(invoice.state, 'posted')

        # when clicking on draft button, it must keep posted because if the pos is open
        # we cannot cancel the invoice.
        invoice.button_draft()
        self.assertEqual(invoice.state, 'posted')

    def test_settle_order_with_lot(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        product = self.env['product.product'].create({
            'name': 'Product A',
            'tracking': 'serial',
            'is_storable': True,
            'lst_price': 10,
        })

        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'lot_id': lot1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'lot_id': lot2.id
        }).action_apply_inventory()

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [
                (0, 0, {
                    'name': 'section line',
                    'display_type': 'line_section',
                }),
                (0, 0, {
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom_qty': 2,
                    'price_unit': product.lst_price,
                })
            ],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_settle_order_with_lot', login="accountman")

    def test_multiple_lots_sale_order(self):
        self.product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': self.product_category.id,
            'tracking': 'lot',
        })

        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.shelf_1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })
        self.shelf_2 = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })

        lot_1001, lot_1002 = self.env['stock.lot'].create([{
                'name': '1001',
                'product_id': self.product.id,
                'location_id': self.shelf_1.id,
            },
            {
                'name': '1002',
                'product_id': self.product.id,
                'location_id': self.shelf_2.id,
            },
            ])
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 1,
            'location_id': self.shelf_1.id,
            'lot_id': lot_1001.id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 2,
            'location_id': self.shelf_2.id,
            'lot_id': lot_1002.id
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 3,
            'location_id': self.shelf_2.id,
            'lot_id': lot_1001.id,
        })
        quants.action_apply_inventory()

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 6,
                'price_unit': self.product.lst_price,
            })],
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_multiple_lots_sale_order_1', login="accountman")
        sale_order.action_confirm()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_multiple_lots_sale_order_2', login="accountman")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_multiple_lots_sale_order_3', login="accountman")
        self.main_pos_config.current_session_id.action_pos_session_close()
        picking = sale_order.pos_order_line_ids.order_id.picking_ids
        self.assertEqual(picking.move_ids.quantity, 6)
        self.assertEqual(len(picking.move_ids.move_line_ids), 3)
        self.assertRecordValues(picking.move_ids.move_line_ids, [
            {'lot_id': lot_1001.id, 'quantity': 3, 'location_id': self.shelf_2.id},
            {'lot_id': lot_1001.id, 'quantity': 1, 'location_id': self.shelf_1.id},
            {'lot_id': lot_1002.id, 'quantity': 2, 'location_id': self.shelf_2.id},
        ])

    def test_settle_groupable_lot_total_amount(self):
        groupable_uom_unit = self.env['uom.uom'].create({
            'name': 'Groupable Unit',
            'is_pos_groupable': True,
        })

        groupable_uom_dozens = self.env['uom.uom'].create({
            'name': 'Groupable Dozens',
            'relative_factor': 12,
            'relative_uom_id': groupable_uom_unit.id,
        })

        self.product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 1.0,
            'taxes_id': False,
            'categ_id': self.product_category.id,
            'tracking': 'lot',
            'uom_id': groupable_uom_unit.id,
        })

        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        self.shelf = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })

        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 10_000,
            'location_id': self.shelf.id,
            'lot_id': self.env['stock.lot'].create({
                'name': '1001',
                'product_id': self.product.id,
                'location_id': self.shelf.id,
            }).id,
        })

        quants.action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 1,
                'product_uom_id': groupable_uom_dozens.id,
                'price_unit': 12.0,
            })],
        })

        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_settle_groupable_lot_total_amount', login="accountman")

    def test_refund_ship_later_qty_delivered(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 5,
                'price_unit': self.product_a.lst_price,
                'product_uom_id': self.product_a.uom_id.id
            })],
        })
        sale_order.action_confirm()

        self.main_pos_config.ship_later = True
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {
           'amount_paid': self.product_a.lst_price * 5,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': self.product_a.lst_price * 5,
           'company_id': self.env.company.id,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': self.partner_a.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': self.product_a.lst_price,
              'product_id': self.product_a.id,
              'price_subtotal': self.product_a.lst_price * 5,
              'price_subtotal_incl': self.product_a.lst_price * 5,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 5,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'payment_ids': [[0,
             0,
             {'amount': self.product_a.lst_price * 5,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'user_id': self.env.uid,
           'uuid': str(uuid.uuid4()),
        }

        data = self.env['pos.order'].sync_from_ui([pos_order])
        pos_order_id = data['pos.order'][0]['id']
        pos_order_record = self.env['pos.order'].browse(pos_order_id)

        pos_order_refund = {
           'amount_paid': -self.product_a.lst_price * 3,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': -self.product_a.lst_price * 3,
           'company_id': self.env.company.id,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': self.partner_a.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': self.product_a.lst_price,
              'product_id': self.product_a.id,
              'price_subtotal': -self.product_a.lst_price * 3,
              'price_subtotal_incl': -self.product_a.lst_price * 3,
              'refund_orderline_ids': [],
              'refunded_orderline_id': pos_order_record.lines[0].id,
              'qty': -3,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'payment_ids': [[0,
             0,
             {'amount': -self.product_a.lst_price * 3,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'user_id': self.env.uid,
           'uuid': str(uuid.uuid4()),
           'shipping_date': '2023-01-01',
        }
        data = self.env['pos.order'].sync_from_ui([pos_order_refund])
        pos_order_refund_id = data['pos.order'][1]['id']
        pos_order_refund_record = self.env['pos.order'].browse(pos_order_refund_id)
        self.assertEqual(sale_order.order_line.qty_delivered, 5)
        for picking in pos_order_refund_record.picking_ids:
            picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 2)

    def test_amount_unpaid_with_downpayment_and_credit_note(self):
        """ Test that amount_unpaid is well calculated when a downpayment is not made in the PoS """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 500,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()

        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 300,
        })
        res = payment.create_invoices()
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.action_post()

        self.assertEqual(sale_order.amount_unpaid, 200.0)

        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        self.assertEqual(sale_order.amount_unpaid, 500.0)

        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })
        res = payment.create_invoices()
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.action_post()

        self.assertEqual(sale_order.amount_unpaid, 0.0)

    def test_settle_changed_price_with_lots(self):
        """
        Tests that when we change the price of a line in the quotation, it will not be reverted when
        settling it through the PoS
        """
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        product_lot_tracked = self.env['product.product'].create({
            'name': 'Settle Lots',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': False,
            'tracking': 'lot',
        })
        self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': product_lot_tracked.id,
                    'product_uom_qty': 1,
                    'price_unit': 120.0,
                }),
                (0, 0, {
                    'product_id': product_lot_tracked.id,
                    'product_uom_qty': 1,
                    'price_unit': 60.0,
                })
            ]
        })
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_settle_changed_price_with_lots', login="accountman")
