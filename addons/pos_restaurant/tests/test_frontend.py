# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.pos_restaurant.tests.test_common import TestPoSRestaurantDataHttpCommon
from odoo import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestFrontend(TestPoSRestaurantDataHttpCommon):

    def test_pos_restaurant(self):
        self.start_pos_tour('pos_restaurant_sync')
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 10.00), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 10.00), ('state', '=', 'paid')]))
        self.start_pos_tour('pos_restaurant_sync_second_login')
        self.assertEqual(0, self.env['pos.order'].search_count([('amount_total', '=', 10.0), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 20.0), ('state', '=', 'draft')]))
        self.assertEqual(2, self.env['pos.order'].search_count([('amount_total', '=', 10.0), ('state', '=', 'paid')]))

    def test_floor_plans_archive(self):
        floors = self.main_floor + self.second_floor
        floors.action_archive()
        self.assertTrue(all(floor.active is False for floor in floors), "All floors should be archived")

    def test_floor_screen(self):
        self.start_pos_tour('FloorScreenTour', login="pos_admin")

    def test_merge_unmerge_table(self):
        self.start_pos_tour('TableMergeUnmergeTour', login="pos_admin")

    def test_control_button(self):
        self.pos_config.is_order_printer = False
        self.start_pos_tour('ControlButtonsTour', login="pos_admin")

    def test_ticket_screen(self):
        self.pos_config.is_order_printer = False
        self.start_pos_tour('PosResTicketScreenTour')

    def test_tip_screen(self):
        self.pos_config.write({'set_tip_after_payment': True, 'iface_tipproduct': True, 'tip_product_id': self.env.ref('point_of_sale.product_product_tip')})
        self.start_pos_tour('PosResTipScreenTour')

        orders = self.env['pos.order'].search([], limit=5, order="id desc")
        order_tips = [o.tip_amount for o in orders]

        # orders order can be different depending on which module is install so we sort the tips
        order_tips.sort()
        self.assertEqual(order_tips, [0.0, 0.4, 1.0, 1.0, 1.5])

        order4 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-00004')], limit=1, order='id desc')
        self.assertEqual(order4.customer_count, 2)

    def test_split_bill_screen(self):
        setup_product_combo_items(self)
        self.pos_config.is_order_printer = False
        self.office_combo.product_variant_id.write({'lst_price': 40})
        self.start_pos_tour('SplitBillScreenTour')
        self.close_session()
        self.start_pos_tour('SplitBillScreenTour2')
        self.close_session()
        self.start_pos_tour('SplitBillScreenTour3')
        self.close_session()
        self.start_pos_tour('SplitBillScreenTour4ProductCombo')
        self.close_session()
        self.start_pos_tour('SplitBillScreenTour5Actions')

    def test_refund_stay_current_table(self):
        self.start_pos_tour('RefundStayCurrentTableTour')

    def test_save_last_preparation_changes(self):
        self.pos_config.write({'printer_ids': False})
        self.start_pos_tour('SaveLastPreparationChangesTour')
        self.assertTrue(self.pos_config.current_session_id.order_ids.last_order_preparation_change, "There should be a last order preparation change")
        self.assertTrue("Awesome" in self.pos_config.current_session_id.order_ids.last_order_preparation_change, "The last order preparation change should contain 'Coca'")

    def test_bill_screen_qrcode_data(self):
        self.pos_config.write({'printer_ids': False})
        self.pos_config.company_id.point_of_sale_use_ticket_qr_code = True
        self.pos_config.company_id.point_of_sale_ticket_portal_url_display_mode = 'qr_code_and_url'
        self.start_pos_tour('BillScreenTour')

    def test_order_tracking(self):
        self.pos_config.write({'order_edit_tracking': True})
        self.start_pos_tour('OrderTrackingTour')
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-00001')], limit=1, order='id desc')
        self.assertTrue(order1.is_edited)

    def test_category_check(self):
        self.category_items.write({'name': 'Another one'})
        self.start_pos_tour('CategLabelCheck')

    def test_change_synced_order(self):
        self.start_pos_tour('OrderChange')

    def test_crm_team(self):
        if self.env['ir.module.module']._get('pos_sale').state != 'installed':
            self.skipTest("'pos_sale' module is required")
        sale_team = self.env['crm.team'].search([], limit=1)
        self.pos_config.crm_team_id = sale_team
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('CrmTeamTour')
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.crm_team_id.id, sale_team.id)

    def test_pos_payment_sync(self):
        self.pos_config.write({'printer_ids': False})
        def assert_payment(lines_count, amount):
            self.assertEqual(len(order.payment_ids), lines_count)
            self.assertEqual(round(sum(payment.amount for payment in order.payment_ids), 2), amount)
        self.start_pos_tour('PoSPaymentSyncTour1')
        order = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(order), 1)
        assert_payment(1, 20.00)
        self.start_pos_tour('PoSPaymentSyncTour2')
        assert_payment(1, 40.00)
        self.start_pos_tour('PoSPaymentSyncTour3')
        assert_payment(2, 60.00)

    def test_preparation_printer_content(self):
        self.printer.write({'product_categories_ids': [(4, self.category_configurables.id)]})
        self.start_pos_tour('PreparationPrinterContent')

    def test_create_floor_tour(self):
        self.start_pos_tour('test_create_floor_tour', login="pos_admin")

    def test_combo_preparation_receipt(self):
        setup_product_combo_items(self)
        self.printer.write({
            'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)]
        })
        self.start_pos_tour('test_combo_preparation_receipt')

    def test_multiple_preparation_printer(self):
        """This test make sure that no empty receipt are sent when using multiple printer with different categories
           The tour will check that we tried did not try to print two receipt. We can achieve that by checking the content
           of the error message. Because we do not have real printer an error message will be displayed, this will contain
           all the receipt that failed to print. If it contains more than 1 it means that we tried to print a second receipt
           and it should not be the case here. The only one we should see is 'Detailed Receipt'
        """
        printer = self.env['pos.printer'].create({
            'name': 'Printer 1',
            'printer_type': 'epson_epos',
            'epson_printer_ip': '0.0.0.1',
            'product_categories_ids': [(4, self.category_items.id)],
        })
        self.pos_config.write({
            'is_order_printer' : True,
            'printer_ids': [(4, printer.id)],
        })
        self.start_pos_tour('MultiPreparationPrinter')

    def test_user_on_residual_order(self):
        self.pos_config.write({'printer_ids': False})
        self.start_pos_tour('LeaveResidualOrder', login="pos_admin")
        self.start_pos_tour('FinishResidualOrder', login="pos_user")
        orders = self.env['pos.order'].search([])
        self.assertEqual(orders[0].user_id.id, self.pos_user.id, "Pos user not registered on order")
        self.assertEqual(orders[1].user_id.id, self.pos_admin.id, "Pos admin not registered on order")

    def test_tax_in_merge_table_order_line(self):
        """
        Test that when merging orders of two tables in POS restaurant, the product tax is applied on the order lines of the destination table.
        """
        self.product_awesome_item.write({'taxes_id': self.tax_sale_a})
        self.product_awesome_article.write({'taxes_id': self.tax_sale_a})
        self.pos_config.is_order_printer = False
        self.start_pos_tour('test_tax_in_merge_table_order_line_tour', login="pos_admin")
        line_1 = self.env['pos.order.line'].search([('full_product_name', '=', 'Awesome Item')])
        line_2 = self.env['pos.order.line'].search([('full_product_name', '=', 'Awesome Article')])
        self.assertEqual(line_1.tax_ids, self.tax_sale_a)
        self.assertEqual(line_2.tax_ids, self.tax_sale_a)
