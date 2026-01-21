# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosStockHttpCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Update user.
        cls.pos_user.write({
            'group_ids': [
                (4, cls.env.ref('stock.group_stock_user').id),
            ]
        })


class TestUi(TestPosStockHttpCommon):

    def test_receipt_screen_tour(self):
        self.tip.write({
            'taxes_id': False
        })
        self.main_pos_config.write({
            'iface_tipproduct': True,
            'tip_product_id': self.tip.id,
            'ship_later': True
        })
        self.start_pos_tour('StockFeedbackScreenTour')
        for order in self.env['pos.order'].search([]):
            self.assertEqual(order.state, 'paid', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

        # check if email from FeedbackScreenTour is properly sent
        email_count = self.env['mail.mail'].search_count([('email_to', '=', 'test@feedbackscreen.com')])
        self.assertEqual(email_count, 1)

    def test_03_pos_with_lots(self):

        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.monitor_stand.tracking = 'lot'
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_03_pos_with_lots', login="pos_user")

    def test_product_information_screen_admin(self):
        '''Consider this test method to contain a test tour with miscellaneous tests/checks that require admin access.
        '''
        self.product_a.available_in_pos = True
        self.pos_admin.write({
            'group_ids': [Command.link(self.env.ref('base.group_system').id)],
        })
        self.main_pos_config.write({
            'is_margins_costs_accessible_to_every_user': True,
        })
        self.assertFalse(self.product_a.is_storable)
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'CheckProductInformation', login="pos_admin")

    def test_change_without_cash_method(self):
        # create bank payment method
        bank_pm = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
            'is_cash_count': False,
            'split_transactions': False,
            'company_id': self.env.company.id,
        })
        self.main_pos_config.write({'payment_method_ids': [(6, 0, bank_pm.ids)], 'ship_later': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'StockPaymentScreenTour2', login="pos_user")

    def test_lot_refund(self):

        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'LotRefundTour', login="pos_user")

    def test_receipt_tracking_method(self):
        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'ReceiptTrackingMethodTour', login="pos_user")

    def test_limited_product_pricelist_loading(self):
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 1)

        limited_category = self.env['pos.category'].create({
            'name': 'Limited Category',
        })
        product_1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'list_price': 100,
            'barcode': '0100100',
            'taxes_id': False,
            'pos_categ_ids': [(4, limited_category.id)],
            'available_in_pos': True,
        })

        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 4,
            'value_ids': [(0, 0, {
                'name': 'White',
                'sequence': 1,
            }), (0, 0, {
                'name': 'Red',
                'sequence': 2,
                'default_extra_price': 50,
            })],
        })

        product_2_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'list_price': 200,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, limited_category.id)],
            'tracking': 'lot',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, color_attribute.value_ids.ids)]
            })],
        })

        # Check that two product variant are created
        self.assertEqual(product_2_template.product_variant_count, 2)
        product_2_template.product_variant_ids[0].write({'barcode': '0100201'})
        product_2_template.product_variant_ids[1].write({'barcode': '0100202'})

        self.env['product.product'].create({
            'name': 'Test Product 3',
            'list_price': 300,
            'barcode': '0100300',
            'taxes_id': False,
            'pos_categ_ids': [(4, limited_category.id)],
            'available_in_pos': True,
        })

        pricelist_item = self.env['product.pricelist.item'].create([{
            'applied_on': '3_global',
            'fixed_price': 50,
        }, {
            'applied_on': '1_product',
            'product_tmpl_id': product_2_template.id,
            'fixed_price': 100,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_1.id,
            'fixed_price': 80,
            'min_quantity': 1,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_1.id,
            'fixed_price': 70,
            'min_quantity': 2,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_2_template.product_variant_ids[1].id,
            'fixed_price': 120,
        }])
        self.main_pos_config.write({
            'iface_available_categ_ids': [],
            'limit_categories': True,
        })
        self.main_pos_config.pricelist_id.write({'item_ids': [(6, 0, pricelist_item.ids)]})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'limitedProductPricelistLoadingStock', login="pos_user")

    def test_multi_product_options(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        chair_multi_attribute = self.env['product.attribute'].create({
            'name': 'Multi',
            'display_type': 'multi',
            'create_variant': 'no_variant',
        })
        chair_multi_value_1 = self.env['product.attribute.value'].create({
            'name': 'Value 1',
            'attribute_id': chair_multi_attribute.id,
        })
        chair_multi_value_2 = self.env['product.attribute.value'].create({
            'name': 'Value 2',
            'attribute_id': chair_multi_attribute.id,
        })
        self.chair_multi_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'attribute_id': chair_multi_attribute.id,
            'value_ids': [(6, 0, [chair_multi_value_1.id, chair_multi_value_2.id])]
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'MultiProductOptionsTour', login="pos_user")

    def test_lot(self):
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product2.id,
            'inventory_quantity': 1,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
            'lot_id': self.env['stock.lot'].create({'name': '1001', 'product_id': product2.id}).id,
        }).sudo().action_apply_inventory()

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'LotTour', login="pos_user")
        two_last_orders = self.env['pos.order'].search([], order='id desc', limit=2)
        order_lot_id = [lot_id.lot_name for lot_id in two_last_orders[1].lines.pack_lot_ids]
        refund_lot_id = [lot_id.lot_name for lot_id in two_last_orders[0].lines.pack_lot_ids]
        self.assertEqual(order_lot_id, refund_lot_id, "In the refund we should find the same lot as in the original order")
        self.assertEqual(two_last_orders[0].state, 'paid')
        self.assertEqual(two_last_orders[1].state, 'paid')
        self.main_pos_config.current_session_id.order_ids.filtered(
            lambda o: o.state != 'paid').state = 'cancel'

        self.main_pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(
            two_last_orders[0].picking_ids.move_line_ids.owner_id.id,
            two_last_orders[1].picking_ids.move_line_ids.owner_id.id,
            "The owner of the refund is not the same as the owner of the original order")

    def test_only_existing_lots(self):
        product = self.env['product.product'].create({
            'name': 'Product with existing lots',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': product.id,
            'inventory_quantity': 1,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
            'lot_id': self.env['stock.lot'].create({'name': '1001', 'product_id': product.id}).id,
        }, {
            'product_id': product.id,
            'inventory_quantity': 1,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
            'lot_id': self.env['stock.lot'].create({'name': '1002', 'product_id': product.id}).id,
        }]).sudo().action_apply_inventory()

        self.main_pos_config.picking_type_id.write({
            "use_create_lots": False,
            "use_existing_lots": True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_only_existing_lots', login="pos_user")

    def test_order_with_existing_serial(self):
        product = self.env['product.product'].create({
            'name': 'Serial Product',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        for sn in ["SN1", "SN2"]:
            self.env['stock.quant'].create({
                'product_id': product.id,
                'inventory_quantity': 1,
                'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
                'lot_id': self.env['stock.lot'].create({'name': sn, 'product_id': product.id}).id,
            }).sudo().action_apply_inventory()
        self.env['stock.picking.type'].search([('name', '=', 'PoS Orders')]).use_create_lots = False

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("test_order_with_existing_serial")

    def test_edit_paid_order(self):
        self.main_pos_config.write({'ship_later': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_edit_paid_order_stock', login="pos_user")
        edited_orders = self.env['pos.order'].search([], limit=2)
        # check edited shiping date
        next_year = date.today().year + 1
        self.assertEqual(edited_orders[0].shipping_date, date(next_year, 5, 30))
        self.assertEqual(edited_orders[0].picking_ids[0].scheduled_date, datetime(next_year, 5, 30, 0, 0, 0))
        # check invoice created
        self.assertTrue(edited_orders[1].account_move)
        self.assertEqual(edited_orders[1].partner_id.name, 'Partner Test 1')

    def test_add_multiple_serials_at_once(self):
        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, "AddMultipleSerialsAtOnce", login="pos_user")

    def test_pos_order_shipping_date(self):
        self.env['res.partner'].create({
            'name': 'Partner Test with Address',
            'street': 'test street',
            'zip': '1234',
            'city': 'test city',
            'country_id': self.env.ref('base.us').id
        })
        self.main_pos_config.write({'ship_later': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            f"/pos/ui?config_id={self.main_pos_config.id}",
            "test_pos_order_shipping_date",
            login="pos_user",
        )

    def test_product_info_product_inventory(self):
        """ Test that the product variant inventory info is correctly displayed in the POS. """
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [
                Command.create({'name': 'Small'}),
                Command.create({'name': 'Large'})
            ],
            'create_variant': 'always',
        })

        product_template = self.env['product.template'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'is_storable': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': size_attribute.id,
                    'value_ids': [Command.link(id) for id in size_attribute.value_ids.ids]
                })
            ]
        })

        for variant in range(len(product_template.product_variant_ids)):
            self.env['stock.quant']._update_available_quantity(product_template.product_variant_ids[variant], self.main_pos_config.warehouse_id.lot_stock_id, (variant + 1) * 100)
            product_template.product_variant_ids[variant].write({'barcode': f'product_variant_{variant}'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_product_info_product_inventory')

    def test_lot_refund_lower_qty(self):
        product = self.env['product.product'].create({
            'name': 'Serial Product',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        for sn in ["SN1", "SN2"]:
            self.env['stock.quant'].create({
                'product_id': product.id,
                'inventory_quantity': 1,
                'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
                'lot_id': self.env['stock.lot'].create({'name': sn, 'product_id': product.id}).id,
            }).sudo().action_apply_inventory()
        self.env['stock.picking.type'].search([('name', '=', 'PoS Orders')]).use_create_lots = False

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("test_lot_refund_lower_qty")

    def test_lot_tracking_without_lot_creation(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        self.main_pos_config.write({
            'available_pricelist_ids': [(6, 0, [pricelist.id])],
            'pricelist_id': pricelist.id,
        })
        self.main_pos_config.picking_type_id.write({
            "use_create_lots": False,
            "use_existing_lots": False,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.monitor_stand.tracking = 'lot'
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_lot_tracking_without_lot_creation', login="pos_user")
