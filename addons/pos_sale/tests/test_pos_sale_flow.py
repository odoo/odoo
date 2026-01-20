# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import format_date
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
import uuid


@tagged('post_install', '-at_install')
class TestPoSSale(TestPointOfSaleHttpCommon):
    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')

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
                (4, self.env.ref('base.group_system').id), # FIXME refacto
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleOrder', login="pos_user")

        #assert that sales order qty are correctly updated
        self.assertEqual(sale_order.order_line.qty_delivered, 3)
        self.assertEqual(sale_order.picking_ids[0].move_ids.product_qty, 2100) # 7 left to deliver => 300 * 7 = 2100
        self.assertEqual(sale_order.picking_ids[0].move_ids.quantity, 0)
        self.assertEqual(sale_order.picking_ids[1].move_ids.product_qty, 300)
        self.assertEqual(sale_order.picking_ids[1].move_ids.quantity, 300) # 1 delivered => 300 * 2 = 600

    def test_settle_order_with_incompatible_partner(self):
        """ If the partner of the sale order is not compatible with the current pos order,
            then a new pos order should be to settle the newly selected sale order.
        """

        product1 = self.env['product.product'].create({
            'name': 'product1',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10,
            'taxes_id': [Command.clear()],
        })
        product2 = self.env['product.product'].create({
            'name': 'product2',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 11,
            'taxes_id': [Command.clear()],
        })
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'Test Partner 2'})
        self.env['sale.order'].sudo().create({
            'partner_id': partner_1.id,
            'partner_shipping_id': partner_2.id,
            'order_line': [(0, 0, {'product_id': product1.id})],
        })
        self.env['sale.order'].sudo().create({
            'partner_id': partner_1.id,
            'partner_shipping_id': partner_1.id,
            'order_line': [(0, 0, {'product_id': product2.id})],
        })
        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrderIncompatiblePartner', login="accountman")

    def test_settle_order_with_different_product(self):
        """This test create an order and settle it in the PoS. But only one of the product is delivered.
            And we need to make sure the quantity are correctly updated on the sale order.
        """
        #create 2 products
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
        #create a sale order with 2 lines
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

    def test_downpayment_refund(self):
        #create a sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()
        #set downpayment product in pos config
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_pos_tour('PosRefundDownpayment', login="accountman")
        self.assertEqual(len(sale_order.order_line), 4)
        self.assertEqual(sale_order.order_line[2].qty_invoiced, 1)
        self.assertEqual(sale_order.order_line[3].qty_invoiced, -1)

    def test_settle_order_unreserve_order_lines(self):
        #create a product category that use the closest location for the removal strategy
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

        #create 2 stock location Shelf 1 and Shelf 2
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

        #get the warehouse
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.sudo().delivery_steps = 'pick_pack_ship'

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        self.env['stock.quant']._update_available_quantity(product_a, warehouse.lot_stock_id, 1)

        #create a sale order with 2 lines
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

    def test_pos_not_groupable_product(self):
        #Create a UoM Category that is not pos_groupable
        uom = self.env['uom.uom'].create({
            'name': 'Test',
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'uom_id': uom.id,
        })
        #create a sale order with product_a
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 3.5,
                'price_unit': 8,  # manually set a different price than the lst_price
                'discount': 10,
            })],
        })
        self.assertEqual(sale_order.amount_total, 28.98)  # 3.5 * 8 * 1.15 * 90%
        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrderNotGroupable', login="accountman")

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

    def test_customer_notes(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """

        #create a sale order with 2 customer notes
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'note': 'Customer note 1',
            'order_line': [(0, 0, {
                'product_id': self.whiteboard_pen.product_variant_id.id,
                'name': self.whiteboard_pen.name,
                'product_uom_qty': 1,
                'price_unit': self.whiteboard_pen.product_variant_id.lst_price,
            }), (0, 0, {
                'name': 'Customer note 2',
                'display_type': 'line_note',
            }), (0, 0, {
                'name': 'Customer note 3',
                'display_type': 'line_note',
            })],
        })

        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrderWithNote', login="accountman")

    def test_order_sales_count(self):
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})
        order = self.env['pos.order'].create({
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
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': current_session.payment_method_ids[0].id,
        })
        order_payment.with_context(**payment_context).check()

        current_session.close_session_from_ui()
        self.env.flush_all()
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        self.assertEqual(self.desk_pad.sales_count, 1)

    def test_untaxed_invoiced_amount(self):
        """Make sure that orders invoiced in the pos gets their untaxed invoiced
           amount updated accordingly"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'lst_price': 5.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
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
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {
           'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': product_a.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 1,
              'tax_ids': []}]],
           'session_id': current_session.id,
           'payment_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'user_id': self.env.uid,
            }

        self.env['pos.order'].sync_from_ui([pos_order])
        self.assertEqual(sale_order.order_line[0].untaxed_amount_invoiced, 10, "Untaxed invoiced amount should be 10")
        self.assertEqual(sale_order.order_line[1].untaxed_amount_invoiced, 0, "Untaxed invoiced amount should be 0")

    def test_order_does_not_remain_in_list(self):
        """Verify that a paid order doesn't remain in the orders list"""

        # Create a sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.whiteboard_pen.product_variant_id.id,
                'name': self.whiteboard_pen.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })

        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosOrderDoesNotRemainInList', login="accountman")

    def test_settle_draft_order_service_product(self):
        """
        Checks that, when settling a draft order (quotation), the quantity set on the corresponding
        PoS order, for service products, is set correctly.
        """

        product_a = self.env['product.product'].create({
            'name': 'Test service product',
            'available_in_pos': True,
            'type': 'service',
            'invoice_policy': 'order',
            'lst_price': 50.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })

        self.assertEqual(sale_order.state, 'draft')

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleDraftOrder', login="accountman")
        self.assertEqual(sale_order.state, 'sale')

    def test_settle_order_change_customer(self):
        """
        When settling an order, the price set on the sol shouldn't reset to
        the sale price of the product when changing customer.
        """
        self.product_a.lst_price = 150
        self.product_a.taxes_id = None
        self.product_a.available_in_pos = True
        self.product_a.name = 'Product A'
        self.env['res.partner'].create({'name': 'A Test Partner AAA'})
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleCustomPrice', login="accountman")

    def test_so_with_downpayment(self):
        self.product_a.available_in_pos = True
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        self.env['sale.advance.payment.inv'].sudo().create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 20,
            'sale_order_ids': so.ids,
        }).create_invoices()
        # Invoice the delivered part from the down payment
        down_payment_invoices = so.invoice_ids
        down_payment_invoices.action_post()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.main_pos_config.down_payment_product_id.write({'active': True})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PoSSaleOrderWithDownpayment', login="accountman")

    def test_downpayment_with_taxed_product(self):
        tax_1 = self.env['account.tax'].create({
            'name': '10',
            'amount': 10,
        })

        tax_2 = self.env['account.tax'].create({
            'name': '5 incl',
            'amount': 5,
            'price_include_override': 'tax_included',
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [tax_1.id],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })

        product_c = self.env['product.product'].create({
            'name': 'Product C',
            'available_in_pos': True,
            'lst_price': 15.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
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
            }), (0, 0, {
                'product_id': product_c.id,
                'name': product_c.name,
                'product_uom_qty': 1,
                'price_unit': product_c.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PoSDownPaymentLinesPerTax', login="accountman")

        # We check the content of the invoice to make sure Product A/B/C only appears only once
        invoice_pdf_content = str(self.env['pos.order'].search([]).account_move._get_invoice_legal_documents('pdf', allow_fallback=True).get('content'))
        self.assertEqual(invoice_pdf_content.count('Product A'), 1)
        self.assertEqual(invoice_pdf_content.count('Product B'), 1)
        self.assertEqual(invoice_pdf_content.count('Product C'), 1)

        for order_line in sale_order.order_line.filtered(lambda l: l.product_id == self.downpayment_product):
            order_line = order_line.with_context(lang=partner_test.lang)
            self.assertIn(format_date(order_line.env, order_line.order_id.date_order), order_line.name)

    def test_settle_so_with_non_pos_groupable_uom(self):
        """
        For products with a non-groupable PoS UoM (e.g., Kg), ensure that when a SO
        uses another UoM (e.g., g), the PoS correctly displays the quantity converted
        back to the original UoM.
        """
        self.component_kg = self.env['product.product'].create({
            'name': 'Pomme de Terre',
            'is_storable': True,
            'available_in_pos': True,
            'taxes_id': False,
            'lst_price': 10.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.component_kg.id,
                'name': self.component_kg.name,
                'product_uom_qty': 500,
                'product_uom_id': self.env.ref('uom.product_uom_gram').id,
                'price_unit': 0.01,
            })],
        })
        sale_order.action_confirm()

        self.start_pos_tour('test_settle_so_with_non_pos_groupable_uom')

    def test_settle_so_with_pos_downpayment(self):
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Apply 10% down payment
        self.main_pos_config.open_ui()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PoSApplyDownpayment', login="accountman")

        invoice = so._create_invoices(final=True)
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 90)

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

    def test_order_sale_team(self):
        self.env['product.product'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': False,
        })
        sale_team = self.env['crm.team'].create({'name': 'Test team'})
        self.main_pos_config.write({'crm_team_id': sale_team})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSaleTeam', login="accountman")
        order = self.env['pos.order'].search([])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.crm_team_id, sale_team)

    def test_show_orders_for_pos_currency_only(self):
        currency = self.env['res.currency'].create({
            'name': 'C',
            'symbol': 'C',
            'rounding': 0.01,
            'currency_unit_label': 'Curr',
            'rate': 1,
        })
        pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist Different Currency',
            'currency_id': currency.id,
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'lst_price': 10,
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
            'pricelist_id': pricelist.id
        })
        sale_order.action_confirm()
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosOrdersListDifferentCurrency', login="pos_admin")

    def test_downpayment_amount_to_invoice(self):
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PoSDownPaymentAmount', login="accountman")
        self.assertEqual(sale_order.amount_to_invoice, 80.0, "Downpayment amount not considered!")
        self.assertEqual(sale_order.amount_invoiced, 20.0, "Downpayment amount not considered!")

        self.assertEqual(sale_order.order_line[2].price_unit, 20)

        # Update delivered quantity of SO line
        sale_order.order_line[0].write({'qty_delivered': 1.0})

        # Let's do the invoice for the remaining amount
        self.env['sale.advance.payment.inv'].sudo().with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({}).create_invoices()

        # Confirm all invoices
        sale_order.invoice_ids.action_post()
        self.assertEqual(sale_order.order_line[2].price_unit, 20)

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
            'is_company': True,
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

    def test_pos_sale_warnings(self):
        self.env['res.partner'].create([
            {'name': 'A Test Customer 1', 'sale_warn_msg': 'Highly infectious disease'},
            {'name': 'A Test Customer 2', 'sale_warn_msg': 'Cannot afford our services'}
        ])
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSaleWarning', login="accountman")

    def test_downpayment_invoice(self):
        """This test check that users that don't have the pos user group can invoice downpayments"""
        self.env['res.partner'].create({'name': 'Test Partner AAA'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()

        self.env['sale.advance.payment.inv'].sudo().with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
        }).create_invoices()

        selected_groups = self.user.group_ids
        self.user.group_ids = self.env.ref('account.group_account_manager') + self.env.ref('sales_team.group_sale_salesman_all_leads')

        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.user.group_ids = selected_groups
        self.assertEqual(downpayment_line.price_unit, 100)

    def test_downpayment_invoice_link(self):
        # Test to check if the final invoice generated from an SO is correctly linked to the downpayment invoice.

        tax = self.env['account.tax'].create({
            'name': 'Base Tax',
            'amount': 15,
        })
        customer = self.env['res.partner'].create({'name': 'Test Partner A'})
        sale_orders = self.env['sale.order'].create([{
            'partner_id': customer.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': [tax.id],
            })],
        } for _ in range(2)])

        sale_orders.action_confirm()

        # CASE 1: downpayment generated in POS, invoice settled in backend
        sale_order = sale_orders[1]
        self.main_pos_config.open_ui()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.start_pos_tour('PoSApplyDownpaymentInvoice')

        downpayment_invoice = sale_order.pos_order_line_ids.order_id.account_move
        self.assertTrue(downpayment_invoice._is_downpayment())

        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({}).create_invoices()

        final_invoice_downpayment_line = sale_order.invoice_ids.invoice_line_ids.filtered(lambda r: r.quantity < 0)

        self.assertEqual(
            final_invoice_downpayment_line._get_downpayment_lines(),
            downpayment_invoice.invoice_line_ids,
        )

        # CASE 2: downpayment generated in POS, invoice settled in POS
        sale_order = sale_orders[0]
        self.start_pos_tour('PoSApplyDownpaymentInvoice2')

        downpayment_invoice = sale_order.pos_order_line_ids.order_id.account_move
        self.assertTrue(downpayment_invoice._is_downpayment())

        self.start_pos_tour('PosSettleAndInvoiceOrder2')

        final_invoice_downpayment_line = sale_order.pos_order_line_ids[-1].order_id.account_move.invoice_line_ids.filtered(lambda r: r.quantity < 0)

        self.assertEqual(
            final_invoice_downpayment_line._get_downpayment_lines(),
            downpayment_invoice.invoice_line_ids,
        )

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

    def test_draft_pos_order_linked_sale_order(self):
        """This test create an order and settle it in the PoS. It will let the PoS order in draft state.
           As the order is still in draft state it shouldn't have impact on invoiced qty of the linked sale order.
        """

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosSettleOrder5', login="accountman")
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

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
        self.main_pos_config.open_ui()
        self.start_pos_tour('PoSSettleQuotation', login="accountman")
        self.assertEqual(order.order_line.qty_delivered, 1)

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

    def test_pos_order_and_invoice_amounts(self):
        payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })
        partner_test = self.env['res.partner'].create({
            'name': 'AAA - Test Partner invoice',
            'property_payment_term_id': payment_term.id,
        })

        tax = self.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        test_product = self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 1000,
            'taxes_id': [(6, 0, [tax.id])],
        })

        self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [
                Command.create({
                    'product_id': test_product.id,
                    'price_unit': test_product.lst_price,
                }),
            ],
        })

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'POSSalePaymentScreenInvoiceOrder', login="accountman")

        order = self.env['pos.order'].search([('partner_id', '=', partner_test.id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.partner_id, partner_test)

        invoice = self.env['account.move'].search([('invoice_origin', '=', order.pos_reference)], limit=1)
        self.assertTrue(invoice)
        self.assertFalse(invoice.invoice_payment_term_id)

        self.assertAlmostEqual(order.amount_total, invoice.amount_total, places=2, msg="Order and Invoice amounts do not match.")

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

    def test_down_payment_displayed(self):
        """
        Tests that a down payment for a Sale Order will be displayed and applied when settling the order
        """
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'lst_price': 10.0,
        })
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        so.action_confirm()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_down_payment_displayed', login="accountman")

    def test_amount_to_invoice(self):
        """
        Checks that the amount to invoice is updated correctly when paying an order in the PoS
        """

        product_a = self.env["product.product"].create(
            {
                "name": "Test service product",
                "available_in_pos": True,
                "type": "service",
                "invoice_policy": "order",
                "lst_price": 100.0,
                "taxes_id": [],
            }
        )

        partner_test = self.env["res.partner"].create({"name": "Test Partner"})

        sale_order = self.env["sale.order"].sudo().create(
            {
                "partner_id": partner_test.id,
                "order_line": [Command.create(
                        {
                            "product_id": product_a.id,
                            "name": product_a.name,
                            "product_uom_qty": 1,
                            "price_unit": product_a.lst_price,
                        },
                    )
                ],
            }
        )
        self.main_pos_config.open_ui()
        order_data = {
            "amount_paid": 100,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 100,
            "session_id": self.main_pos_config.current_session_id.id,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "pack_lot_ids": [],
                    "price_unit": 100.0,
                    "product_id": self.product_a.id,
                    "price_subtotal": 100.0,
                    "price_subtotal_incl": 100.0,
                    "tax_ids": [],
                    "sale_order_line_id": sale_order.order_line[0].id,
                    "sale_order_origin_id": sale_order.id,
                    "qty": 1,
                }),
            ],
            "name": "Order 12345-123-1234",
            "partner_id": self.partner_a.id,
            "sequence_number": 2,
            "payment_ids": [
                    Command.create({
                        "amount": 100,
                        "name": fields.Datetime.now(),
                        "payment_method_id": self.main_pos_config.payment_method_ids[0].id,
                    }),
            ],
            "uuid": "12345-123-1234",
            "last_order_preparation_change": "{}",
            "user_id": self.env.uid,
            "to_invoice": True,
        }
        self.assertEqual(sale_order.amount_to_invoice, 100.0, "Amount to invoice should be 100.0")
        self.env['pos.order'].sync_from_ui([order_data])
        self.assertEqual(sale_order.amount_to_invoice, 0.0, "Amount to invoice should be 0.0")

    def test_payment_terms_with_early_discount(self):
        """Make sure that orders invoiced in the pos do not use payment terms with early discount"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        payment_terms = self.env['account.payment.term'].create({
            'name': "Test Payment Term",
            'early_discount': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100,
                'nb_days': 45,
            })]
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'payment_term_id': payment_terms.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': product_a.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 1,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'payment_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'uuid': '00044-003-0014',
           'user_id': self.env.uid}

        pos_order_id = self.env['pos.order'].sync_from_ui([pos_order])['pos.order'][0]['id']
        pos_order = self.env['pos.order'].browse(pos_order_id)
        self.assertFalse(pos_order.account_move.invoice_payment_term_id)

    def test_sale_order_fp_different_from_partner_one(self):
        """
        Tests that the fiscal position of the sale order is not the same as the partner's fiscal position.
        The PoS should always use the fiscal position of the sale order when settling it.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        tax = self.env['account.tax'].create({
            'name': 'Base Tax',
            'amount': 15,
        })
        fp_1 = self.env['account.fiscal.position'].create({
            'name': "Partner FP",
        })
        fp_2 = self.env['account.fiscal.position'].create({
            'name': "Sale Order FP",
        })
        tax_override_1 = self.env['account.tax'].create({
            'name': 'Tax Override 1',
            'amount': 100,
            'amount_type': 'percent',
            'fiscal_position_ids': [fp_1.id],
            'original_tax_ids': [tax.id],
        })
        tax_override_2 = self.env['account.tax'].create({
            'name': 'Tax Override 2',
            'amount': 0,
            'amount_type': 'percent',
            'fiscal_position_ids': [fp_2.id],
            'original_tax_ids': [tax.id],
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [tax.id],
        })
        partner_test = self.env['res.partner'].create({
            'name': 'Test Partner',
            'property_account_position_id': fp_1.id,
        })
        sale_a = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        sale_b = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'fiscal_position_id': fp_2.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'default_fiscal_position_id': False,
        })
        self.assertEqual(sale_a.fiscal_position_id, fp_1, "Sale order should have the fiscal position of the partner")
        self.assertEqual(sale_a.amount_total, 20, "Sale order amount should be 20 with the tax override 1")
        self.assertEqual(sale_a.amount_untaxed, 10, "Sale order untaxed amount should be 10 with the tax override 1")
        self.assertEqual(sale_b.fiscal_position_id, fp_2, "Sale order should have the fiscal position set on the sale order")
        self.assertEqual(sale_b.amount_total, 10, "Sale order amount should be 10 with the tax override 2")
        self.assertEqual(sale_b.amount_untaxed, 10, "Sale order untaxed amount should be 10 with the tax override 2")
        self.start_pos_tour("test_sale_order_fp_different_from_partner_one", login="accountman")

        pos_order_a = self.env['pos.order'].search([('fiscal_position_id', '=', fp_1.id)], limit=1, order='id desc')
        pos_order_b = self.env['pos.order'].search([('fiscal_position_id', '=', fp_2.id)], limit=1, order='id desc')
        self.assertEqual(pos_order_a.amount_total, 20, "PoS order amount should be 20 with the tax override 1")
        self.assertEqual(pos_order_a.amount_tax, 10, "PoS order untaxed amount should be 10 with the tax override 1")
        self.assertEqual(pos_order_a.lines[0].tax_ids, tax_override_1, "PoS order should have the tax override 1")
        self.assertEqual(pos_order_b.amount_total, 10, "PoS order amount should be 10 with the tax override 2")
        self.assertEqual(pos_order_b.amount_tax, 0, "PoS order untaxed amount should be 10 with the tax override 2")
        self.assertEqual(pos_order_b.lines[0].tax_ids, tax_override_2, "PoS order should have the tax override 2")

    def test_quantity_updated_settle(self):
        """
        Tests that the quantity is updated when partially settling an order, so that the
        settle displays the right amount that still needs to be settled.
        """
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'lst_price': 10.0,
        })
        self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 5,
                'price_unit': product_a.lst_price,
            })]
        })
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_quantity_updated_settle', login="accountman")

    def test_settle_order_with_different_uom(self):
        """Verify that a qty has changed according to UOM"""
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        test_partner = self.env['res.partner'].create({'name': 'Test Partner'})
        # Create a sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': test_partner.id,
            'order_line': [Command.create({
                    'product_id': product_a.id,
                    'name': product_a.name,
                    'product_uom_qty': 1,
                    'product_uom_id':  self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': product_a.lst_price,
                })]
        })
        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_pos_tour('PoSSettleQuotation', login="accountman")
        pos_order = self.env['pos.order'].search([('partner_id', '=', test_partner.id)], limit=1)

        self.assertEqual(pos_order.lines[0].qty, 12.0, "quantity should be 12.0")
        self.assertEqual(pos_order.lines[0].price_unit, 0.83, "price of product should be 0.83")

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

        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 1,
            'location_id': self.shelf_1.id,
            'lot_id': self.env['stock.lot'].create({
                'name': '1001',
                'product_id': self.product.id,
                'location_id': self.shelf_1.id,
            }).id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 2,
            'location_id': self.shelf_2.id,
            'lot_id': self.env['stock.lot'].create({
                'name': '1002',
                'product_id': self.product.id,
                'location_id': self.shelf_2.id,
            }).id,
        })
        quants.action_apply_inventory()

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 3,
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
        self.assertEqual(picking.move_ids.quantity, 3)
        self.assertEqual(len(picking.move_ids.move_line_ids), 2)
        self.assertEqual(picking.move_ids.move_line_ids[0].lot_id.name, '1001')
        self.assertEqual(picking.move_ids.move_line_ids[0].quantity, 1)
        self.assertEqual(picking.move_ids.move_line_ids[1].lot_id.name, '1002')
        self.assertEqual(picking.move_ids.move_line_ids[1].quantity, 2)

    def test_selected_partner_quotation_loading(self):
        """
        Tests that when a partner is selected in the PoS, then a quotation for this partner is loaded
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
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
        partner_1 = self.env['res.partner'].create({'name': 'A Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'A Test Partner 2'})
        self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        self.env['sale.order'].create({
            'partner_id': partner_2.id,
            'order_line': [(0, 0, {
                'product_id': product_b.id,
                'product_uom_qty': 2,
                'price_unit': product_b.lst_price,
            })]
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_selected_partner_quotation_loading', login="accountman")

    def test_ecommerce_paid_order_is_hidden_in_pos(self):
        """
        Tests that a Sale Order fully paid via a payment.transaction (eCommerce)
        does not appear in the list of orders fetched by the Point of Sale.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        partner_1 = self.env['res.partner'].create({'name': 'A Test Partner 1'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 2,
                'price_unit': product_a.lst_price
            })]
        })
        provider = self.env['payment.provider'].create({
            'name': 'Test',
        })
        transaction = self.env['payment.transaction'].create({
            'provider_id': provider.id,
            'payment_method_id': self.env.ref('payment.payment_method_unknown').id,
            'amount': sale_order.amount_total,
            'currency_id': sale_order.currency_id.id,
            'partner_id': sale_order.partner_id.id,
            'sale_order_ids': [(6, 0, [sale_order.id])],
        })
        transaction._set_done()
        sale_order.invalidate_recordset(['transaction_ids'])

        self.assertEqual(
            sale_order.amount_unpaid, 0.0,
            "The amount_unpaid for the SO should be 0 after a successful transaction."
        )
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_ecommerce_paid_order_is_hidden_in_pos', login="accountman")

    def test_ecommerce_unpaid_order_is_shown_in_pos(self):
        """
        Tests that a Sale Order fully paid via a payment.transaction (eCommerce)
        does not appear in the list of orders fetched by the Point of Sale.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        partner_1 = self.env['res.partner'].create({'name': 'A Test Partner 1'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 2,
                'price_unit': product_a.lst_price
            })]
        })
        self.assertEqual(
            sale_order.amount_unpaid, sale_order.amount_total,
            "The amount_unpaid for the SO should not be 0 if there are no transactions."
        )
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_ecommerce_unpaid_order_is_shown_in_pos', login="accountman")

    def test_backend_settle_refund(self):
        """Make sure that sale orders settled in PoS and refunded in the backend get their invoiced quantity updated correctly."""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {
           'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': product_a.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 1,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'payment_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'user_id': self.env.uid,
           'uuid': str(uuid.uuid4()),
            }

        data = self.env['pos.order'].sync_from_ui([pos_order])
        self.assertEqual(sale_order.order_line.qty_invoiced, 1)
        pos_order_id = data['pos.order'][0]['id']
        pos_order_record = self.env['pos.order'].browse(pos_order_id)
        refund_action = pos_order_record.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])
        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        })

        self.env.flush_all()
        refund_payment.with_context(**payment_context).check()
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)

    def test_settle_order_with_multiple_uom(self):
        """ Verify that a sale order with multiple UoM can be settled from the PoS."""
        uom_a, uom_b = self.env['uom.uom'].create([{
            "name": "UoM A"
        }, {
            "name": "UoM B"
        }])

        product_a, product_b = self.env['product.product'].create([{
            "name": "Product A",
            "available_in_pos": True,
            "is_storable": True,
            "lst_price": 10.0,
            "uom_id": uom_a.id,
            "taxes_id": [],
        }, {
            "name": "Product B",
            "available_in_pos": True,
            "is_storable": True,
            "lst_price": 20.0,
            "uom_id": uom_b.id,
            "taxes_id": [],
        }])

        sale_order = self.env["sale.order"].sudo().create({
            "partner_id": self.env['res.partner'].create({'name': 'Test Partner'}).id,
            "order_line": [
                (0, 0, {
                    "product_id": product_a.id,
                    "name": product_a.name,
                    "product_uom_qty": 2,
                    "product_uom_id": uom_a.id,
                    "price_unit": product_a.lst_price,
                }),
                (0, 0, {
                    "product_id": product_b.id,
                    "name": product_b.name,
                    "product_uom_qty": 3,
                    "product_uom_id": uom_b.id,
                    "price_unit": product_b.lst_price,
                }),
            ],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_pos_tour('PoSSettleQuotation', login="accountman")

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
