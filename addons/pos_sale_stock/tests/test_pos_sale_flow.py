# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from odoo.addons.pos_stock.tests.test_frontend import TestPosStockHttpCommon
from odoo.addons.pos_sale.tests.test_pos_sale_flow import TestPoSSale


class TestPoSSaleStock(TestPosStockHttpCommon, TestPoSSale):

    _test_user_groups = None  # FIXME list needed groups

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
        self._sync_paid_pos_order([{
            'product': self.kit,
            'qty': 2,
            'price_unit': self.kit.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=sale_order.partner_id)

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
        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=sale_order.partner_id)

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

    def test_settle_quotation_delivered_qty(self):
        """ Test if a quotation (unconfirmed sale order) is settled in the PoS, the delivered quantity is updated correctly """

        product1 = self.env['product.product'].create({
            'name': 'product1',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10,
            'taxes_id': [Command.clear()],
        })
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        order = self.env['sale.order'].sudo().create({
            'partner_id': partner_1.id,
            'order_line': [Command.create({'product_id': product1.id})],
        })
        self._sync_paid_pos_order([{
            'product': product1,
            'qty': 1,
            'price_unit': 10,
            'extra_values': {
                'sale_order_line_id': order.order_line.id,
                'sale_order_origin_id': order.id,
            },
        }], partner=partner_1)
        self.assertEqual(order.order_line.qty_delivered, 1)

    def test_settle_order_with_different_uom_delivered_qty(self):
        """ Test that settling a sale order line sold in another UoM updates its delivered quantity """

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        test_partner = self.env['res.partner'].create({'name': 'Test Partner'})
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': test_partner.id,
            'order_line': [Command.create({
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        # The PoS sells the 12 units of the dozen ordered.
        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 12.0,
            'price_unit': 0.83,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=test_partner)

        # The delivered quantity is converted back in the unit of the sale order line.
        self.assertEqual(sale_order.order_line.qty_delivered, 1.0, "1 dozen should be delivered")

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

        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=sale_order.partner_id)

        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.picking_ids.mapped('state'), ['cancel'])

    def test_settle_order_with_multistep_delivery_receipt(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """
        if not self.env["ir.module.module"].search([("name", "=", "purchase"), ("state", "=", "installed")]):
            self.skipTest("purchase module is required for this test")

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        warehouse.reception_steps = 'three_steps'
        route_mto = warehouse.mto_pull_id.route_id
        route_mto.active = True
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
            'route_ids': [Command.set([route_mto.id])],
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
        order_id = self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=self.partner_test, shipping_date=fields.Date.today())
        order = self.env['pos.order'].browse(order_id)

        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.picking_ids.state, 'assigned')
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
        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order_single.order_line[0].id,
                'sale_order_origin_id': sale_order_single.id,
            },
        }], partner=partner_test, shipping_date=fields.Date.today())
        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order_multi.order_line[0].id,
                'sale_order_origin_id': sale_order_multi.id,
            },
        }, {
            'product': product_b,
            'qty': 1,
            'price_unit': product_b.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order_multi.order_line[1].id,
                'sale_order_origin_id': sale_order_multi.id,
            },
        }], partner=partner_test, shipping_date=fields.Date.today())

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
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})

        pos_order = self._create_pos_order([{
            'product': self.desk_pad.product_variant_id,
            'taxes': self.env['account.tax'],
            'extra_values': {'name': "OL/0001"},
        }], partner=partner_1)

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
        sale_order.action_confirm()
        self._sync_paid_pos_order([
            {
                'product': self.product,
                'qty': 4,
                'price_unit': self.product.lst_price,
                'extra_values': {
                    'pack_lot_ids': [[0, 0, {'lot_name': '1001'}]],
                    'sale_order_line_id': sale_order.order_line[0].id,
                    'sale_order_origin_id': sale_order.id,
                },
            },
            {
                'product': self.product,
                'qty': 2,
                'price_unit': self.product.lst_price,
                'extra_values': {
                    'pack_lot_ids': [[0, 0, {'lot_name': '1002'}]],
                    'sale_order_line_id': sale_order.order_line[0].id,
                    'sale_order_origin_id': sale_order.id,
                },
            },
        ], partner=sale_order.partner_id)
        self.main_pos_config.current_session_id.close_session_from_ui()
        picking = sale_order.pos_order_line_ids.order_id.picking_ids
        self.assertEqual(picking.move_ids.quantity, 6)
        self.assertEqual(len(picking.move_ids.move_line_ids), 3)
        self.assertRecordValues(picking.move_ids.move_line_ids, [
            {'lot_id': lot_1001.id, 'quantity': 3, 'location_id': self.shelf_2.id},
            {'lot_id': lot_1001.id, 'quantity': 1, 'location_id': self.shelf_1.id},
            {'lot_id': lot_1002.id, 'quantity': 2, 'location_id': self.shelf_2.id},
        ])

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

        pos_order_id = self._sync_paid_pos_order([{
            'product': self.product_a,
            'qty': 5,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'pack_lot_ids': [],
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=self.partner_a, to_invoice=True)
        pos_order_record = self.env['pos.order'].browse(pos_order_id)

        pos_order_refund_id = self._sync_paid_pos_order([{
            'product': self.product_a,
            'qty': -3,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'pack_lot_ids': [],
                'refund_orderline_ids': [],
                'refunded_orderline_id': pos_order_record.lines[0].id,
            },
        }], partner=self.partner_a, to_invoice=True, is_refund=True, shipping_date='2023-01-01')
        pos_order_refund_record = self.env['pos.order'].browse(pos_order_refund_id)
        # For both the normal refund and ship later + refund cases, we will create a picking with a negative quantity and validate it immediately.
        self.assertEqual(len(pos_order_refund_record.picking_ids), 1)
        self.assertEqual(pos_order_refund_record.picking_ids.state, 'done')
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

    def test_settle_cancelled_sale_order(self):
        """When settling a cancelled (reset to draft) SO in PoS,
        the PoS picking should include moves for its products."""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': [Command.clear()],
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 20.0,
            'taxes_id': [Command.clear()],
        })
        partner = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({'product_id': product_a.id, 'product_uom_qty': 1}),
                Command.create({'product_id': product_b.id, 'product_uom_qty': 1}),
            ],
        })
        sale_order.action_confirm()
        sale_order._action_cancel()
        sale_order.action_draft()

        self._sync_paid_pos_order([{
            'product': product,
            'qty': 1,
            'price_unit': product.lst_price,
            'extra_values': {
                'sale_order_line_id': so_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        } for product, so_line in zip([product_a, product_b], sale_order.order_line)], partner=partner)

        pos_order = sale_order.pos_order_line_ids.order_id
        pos_shipped_products = pos_order.picking_ids.filtered(lambda p: p.state == 'done').move_ids.product_id
        self.assertEqual(pos_shipped_products, product_a | product_b)

    def test_refund_ship_later_qty_delivered_backend(self):
        "This test make sure that an order refunded in the backend has correct qty_delivered/invoiced on the original sale order"
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 5,
                'price_unit': self.product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.main_pos_config.ship_later = True

        pos_order_id = self._sync_paid_pos_order([{
            'product': self.product_a,
            'qty': 5,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'pack_lot_ids': [],
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=self.partner_a, to_invoice=True)
        pos_order_record = self.env['pos.order'].browse(pos_order_id)
        self.assertEqual(sale_order.order_line.qty_delivered, 5)
        self.assertEqual(sale_order.order_line.qty_invoiced, 5)
        pos_order_refund_record = pos_order_record._refund()
        payment_context = {"active_ids": pos_order_refund_record.ids, "active_id": pos_order_refund_record.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': -5000,
            'payment_method_id': self.bank_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        for picking in pos_order_refund_record.picking_ids:
            picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)

    def test_variant_popup_qty_free(self):
        """
        Tests that the variant popup will correctly display the qty_free instead
        of the qty_remaining, like the other popups.
        """
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2',
            'company_id': self.env.company.id,
        })
        color = self.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'always',
        })
        black, white = self.env['product.attribute.value'].create([
            {'name': 'Black', 'attribute_id': color.id},
            {'name': 'White', 'attribute_id': color.id}
        ])
        product_template = self.env['product.template'].create({
            'name': 'Color Product',
            'available_in_pos': True,
            'is_storable': True,
            'tracking': 'lot',
            'attribute_line_ids': [Command.create({
                'attribute_id': color.id,
                'value_ids': [Command.set([black.id, white.id])]
            })]
        })

        black_product = product_template.product_variant_ids.filtered(
            lambda p: black in p.product_template_attribute_value_ids.product_attribute_value_id
        )
        lot_black = self.env['stock.lot'].create({
            'name': 'LOT1',
            'product_id': black_product.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': black_product.id,
            'inventory_quantity': 50,
            'location_id': warehouse_2.lot_stock_id.id,
            'lot_id': lot_black.id,
        }).action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'warehouse_id': warehouse_2.id,
            'order_line': [Command.create({
                'product_id': black_product.id,
                'product_uom_qty': 50,
                'price_unit': 15.0,
            })]
        })
        sale_order.action_confirm()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_variant_popup_qty_free', login="pos_user")
