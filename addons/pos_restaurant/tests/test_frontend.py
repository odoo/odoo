# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestFrontendCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.food_category = cls.env['pos.category'].create({'name': 'Food', 'sequence': 1})
        cls.drinks_category = cls.env['pos.category'].create({'name': 'Drinks', 'sequence': 2})

        cls.printer = cls.env['pos.printer'].create({
            'name': 'Drinks Printer',
            'epson_printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [cls.drinks_category.id]
        })

        cls.main_pos_config.write({
            'module_pos_restaurant': True,
            'iface_splitbill': True,
            'iface_printbill': True,
            'is_order_printer': True,
            'printer_ids': [(4, cls.printer.id)],
            'limit_categories': True,
            'iface_available_categ_ids': [(4, cls.food_category.id), (4, cls.drinks_category.id)],
        })

        cls.env['ir.default'].set(
            'res.partner',
            'property_account_receivable_id',
            cls.account_receivable.id,
            company_id=cls.main_company.id,
        )

        cls.setup_floor_and_tables(cls)

        cls.setup_restaurant_product(cls)

    def setup_floor_and_tables(self):
        self.pos_config.floor_ids.unlink()

        self.main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.second_floor = self.env['restaurant.floor'].create({
            'name': 'Second Floor',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        self.main_floor_table_5 = self.env['restaurant.table'].create([{
            'table_number': 5,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 100,
        }])
        self.env['restaurant.table'].create([{
            'table_number': 4,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 350,
            'position_v': 100,
        },
        {
            'table_number': 2,
            'floor_id': self.main_floor.id,
            'seats': 4,
            'position_h': 250,
            'position_v': 100,
        },
        {

            'table_number': 1,
            'floor_id': self.second_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 100,
            'position_v': 150,
        },
        {
            'table_number': 3,
            'floor_id': self.second_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 250,
        }])

    def setup_restaurant_product(self):
        product_obj = self.env['product.product']
        self.coca_cola = product_obj.create({
            'name': 'Coca-Cola',
            'list_price': 2.20,
            'weight': 0.01,
            'available_in_pos': True,
            'pos_categ_ids': [(4, self.drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })
        self.water = product_obj.create({
            'name': 'Water',
            'list_price': 2.20,
            'weight': 0.01,
            'available_in_pos': True,
            'pos_categ_ids': [(4, self.drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })
        self.minute_maid = product_obj.create({
            'name': 'Minute Maid',
            'list_price': 2.20,
            'weight': 0.01,
            'available_in_pos': True,
            'pos_categ_ids': [(4, self.drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })
        self.sandwich = product_obj.create({
            'name': 'Sandwich',
            'list_price': 2.20,
            'weight': 0.01,
            'available_in_pos': True,
            'pos_categ_ids': [(4, self.food_category.id)],
            'taxes_id': [(6, 0, [])],
        })
        # multiple categories product
        self.multi_catg_product = product_obj.create({
            'name': 'Test Multi Category Product',
            'list_price': 2.20,
            'weight': 0.01,
            'available_in_pos': True,
            'pos_categ_ids': [(4, self.drinks_category.id), (4, self.food_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        # Configurable Chair (variant product)
        self.configurable_chair.write({
            'pos_categ_ids': [(4, self.drinks_category.id)],  # will put it as a drink for convenience
            'list_price': 5.10,
            'active': True,
            'taxes_id': False,
        })

        self.office_combo.write({'pos_categ_ids': [(4, self.drinks_category.id)]})
        self.office_combo.combo_ids.combo_item_ids.product_id.write({'pos_categ_ids': [(4, self.drinks_category.id)]})


class TestFrontend(TestFrontendCommon):

    def test_01_pos_restaurant(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('pos_restaurant_sync')

        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

        self.start_pos_tour('pos_restaurant_sync_second_login')

        self.assertEqual(0, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 2.2), ('state', '=', 'draft')]))
        self.assertEqual(2, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

    def test_02_others(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour')
        self.start_pos_tour('FloorScreenTour', login="pos_admin")
        self.start_pos_tour('TableMergeUnmergeTour', login="pos_admin")

    def test_02_others_bis(self):
        # disable kitchen printer to avoid printing errors
        self.pos_config.is_order_printer = False
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('ControlButtonsTour', login="pos_admin")

    def test_04_ticket_screen(self):
        self.pos_config.is_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PosResTicketScreenTour')

    def test_05_tip_screen(self):
        self.pos_config.write({'set_tip_after_payment': True})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PosResTipScreenTour')

        orders = self.env['pos.order'].search([], limit=5, order="id desc")
        order_tips = [o.tip_amount for o in orders]

        # orders order can be different depending on which module is install so we sort the tips
        order_tips.sort()
        self.assertEqual(order_tips, [0.0, 0.4, 1.0, 1.0, 1.5])

        order4 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-00004')], limit=1, order='id desc')
        self.assertEqual(order4.customer_count, 2)

    def test_06_split_bill_screen(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour2')

    def test_07_split_bill_screen(self):
        # disable kitchen printer to avoid printing errors
        self.pos_config.is_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour3')

    def test_08_refund_stay_current_table(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('RefundStayCurrentTableTour')

    def test_09_combo_split_bill(self):
        self.office_combo.product_variant_id.write({'lst_price': 40})
        # disable kitchen printer to avoid printing errors
        self.pos_config.is_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour4ProductCombo')

    def test_10_save_last_preparation_changes(self):
        self.pos_config.write({'printer_ids': False})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SaveLastPreparationChangesTour')
        self.assertTrue(self.pos_config.current_session_id.order_ids.last_order_preparation_change, "There should be a last order preparation change")
        self.assertTrue("Coca" in self.pos_config.current_session_id.order_ids.last_order_preparation_change, "The last order preparation change should contain 'Coca'")

    def test_12_order_tracking(self):
        self.pos_config.write({'order_edit_tracking': True})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('OrderTrackingTour')
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-00001')], limit=1, order='id desc')
        self.assertTrue(order1.is_edited)

    def test_13_category_check(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('CategLabelCheck')

    def test_14_change_synced_order(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('OrderChange')

    def test_13_crm_team(self):
        if self.env['ir.module.module']._get('pos_sale').state != 'installed':
            self.skipTest("'pos_sale' module is required")
        sale_team = self.env['crm.team'].search([], limit=1)
        self.pos_config.crm_team_id = sale_team
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('CrmTeamTour')
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.crm_team_id.id, sale_team.id)

    def test_14_pos_payment_sync(self):
        self.pos_config.write({'printer_ids': False})
        self.pos_config.with_user(self.pos_user).open_ui()
        def assert_payment(lines_count, amount):
            self.assertEqual(len(order.payment_ids), lines_count)
            self.assertEqual(round(sum(payment.amount for payment in order.payment_ids), 2), amount)
        self.start_pos_tour('PoSPaymentSyncTour1')
        order = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(order), 1)
        assert_payment(1, 2.2)
        self.start_pos_tour('PoSPaymentSyncTour2')
        assert_payment(1, 4.4)
        self.start_pos_tour('PoSPaymentSyncTour3')
        assert_payment(2, 6.6)

    def test_15_split_bill_screen_actions(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour5Actions')

    def test_preparation_printer_content(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationPrinterContent')

    def test_create_floor_tour(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_create_floor_tour', login="pos_admin")

    def test_combo_preparation_receipt(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_combo_preparation_receipt')

    def test_multiple_preparation_printer(self):
        """This test make sure that no empty receipt are sent when using multiple printer with different categories
           The tour will check that we tried did not try to print two receipt. We can achieve that by checking the content
           of the error message. Because we do not have real printer an error message will be displayed, this will contain
           all the receipt that failed to print. If it contains more than 1 it means that we tried to print a second receipt
           and it should not be the case here. The only one we should see is 'Detailed Receipt'
        """
        # Food Printer
        printer_2 = self.env['pos.printer'].create({
            'name': 'Food Printer',
            'printer_type': 'epson_epos',
            'epson_printer_ip': '0.0.0.0',
            'product_categories_ids': [Command.set(self.food_category.ids)],
        })

        self.main_pos_config.write({
            'printer_ids': [Command.set([self.printer.id, printer_2.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('MultiPreparationPrinter')

    def test_user_on_residual_order(self):
        self.pos_config.write({'printer_ids': False})
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('LeaveResidualOrder', login="pos_admin")
        self.start_pos_tour('FinishResidualOrder', login="pos_user")
        orders = self.env['pos.order'].search([])
        self.assertEqual(orders[0].user_id.id, self.pos_user.id, "Pos user not registered on order")
        self.assertEqual(orders[1].user_id.id, self.pos_admin.id, "Pos admin not registered on order")

    def test_tax_in_merge_table_order_line(self):
        """
        Test that when merging orders of two tables in POS restaurant, the product tax is applied on the order lines of the destination table.
        """
        self.coca_cola.write({'taxes_id': self.tax10})
        self.water.write({'taxes_id': self.tax10})
        self.pos_config.is_order_printer = False

        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_tax_in_merge_table_order_line_tour', login="pos_admin")

        line_1 = self.env['pos.order.line'].search([('full_product_name', '=', 'Coca-Cola')])
        line_2 = self.env['pos.order.line'].search([('full_product_name', '=', 'Water')])
        self.assertEqual(line_1.tax_ids, self.tax10)
        self.assertEqual(line_2.tax_ids, self.tax10)

    def test_multiple_preparation_printer_different_categories(self):
        """This test make sure that no empty receipt are sent when using multiple printer with different categories
           The tour will check that we tried did not try to print two receipt. We can achieve that by checking the content
           of the error message. Because we do not have real printer an error message will be displayed, this will contain
           all the receipt that failed to print. If it contains more than 1 it means that we tried to print a second receipt
           and it should not be the case here. The only one we should see is 'Detailed Receipt'
        """
        printer2 = self.env['pos.printer'].create({
            'name': 'Food Printer',
            'printer_type': 'epson_epos',
            'epson_printer_ip': '0.0.0.0',
            'product_categories_ids': [Command.set(self.food_category.ids)],
        })

        self.main_pos_config.write({
            'is_order_printer': True,
            'printer_ids': [Command.set([self.printer.id, printer2.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'test_multiple_preparation_printer_different_categories', login="pos_user")
