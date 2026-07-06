# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command
import json
from datetime import datetime, timedelta

@odoo.tests.tagged('post_install', '-at_install')
class TestFrontendCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)

        food_category = cls.env['pos.category'].create({'name': 'Food', 'sequence': 1})
        drinks_category = cls.env['pos.category'].create({'name': 'Drinks', 'sequence': 2})
        breads_category = cls.env['pos.category'].create({'name': 'Breads', 'sequence': 3})

        printer = cls.env['pos.printer'].create({
            'name': 'Preparation Printer',
            'printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [drinks_category.id],
            'use_type': 'preparation',
        })

        main_company = cls.env.company
        test_sale_journal_2 = cls.env['account.journal'].create({
            'name': 'Sales Journal - Test2',
            'code': 'TSJ2',
            'type': 'sale',
            'company_id': main_company.id
            })
        cash_journal_2 = cls.env['account.journal'].create({
            'name': 'Cash 2',
            'type': 'cash',
            'company_id': main_company.id,
        })
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Bar Prout',
            'module_pos_restaurant': True,
            'iface_printbill': True,
            'use_order_printer': True,
            'preparation_printer_ids': [(4, printer.id)],
            'iface_tipproduct': False,
            'company_id': cls.env.company.id,
            'journal_id': test_sale_journal_2.id,
            'invoice_journal_id': test_sale_journal_2.id,
            'payment_method_ids': [
                (4, cls.bank_payment_method.id),
                (0, 0, {
                    'name': 'Cash',
                    'split_transactions': False,
                    'receivable_account_id': cls.account_receivable.id,
                    'journal_id': cash_journal_2.id,
                })
            ],
        })
        cls.main_pos_config = cls.pos_config

        cls.pos_config.floor_ids.unlink()

        cls.main_floor = cls.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, cls.pos_config.id)],
        })
        cls.second_floor = cls.env['restaurant.floor'].create({
            'name': 'Second Floor',
            'pos_config_ids': [(4, cls.pos_config.id)],
        })

        cls.main_floor_table_5 = cls.env['restaurant.table'].create([{
            'table_number': 5,
            'floor_id': cls.main_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 100, 'left': 100, 'width': 100, 'height': 100, 'color': 'green'},
        }])
        cls.env['restaurant.table'].create([{
            'table_number': 4,
            'floor_id': cls.main_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 100, 'left': 350, 'width': 100, 'height': 100, 'color': 'green'},
        },
        {
            'table_number': 2,
            'floor_id': cls.main_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 100, 'left': 250, 'width': 100, 'height': 100, 'color': 'green'},
        },
        {

            'table_number': 1,
            'floor_id': cls.second_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 150, 'left': 100, 'width': 100, 'height': 100, 'color': 'green'},
        },
        {
            'table_number': 3,
            'floor_id': cls.second_floor.id,
            'seats': 4,
            'floor_plan_layout': {'top': 250, 'left': 100, 'width': 100, 'height': 100, 'color': 'green'},
        }])

        cls.env['ir.default'].set(
            'res.partner',
            'property_account_receivable_id',
            cls.account_receivable.id,
            company_id=main_company.id,
        )

        cls.coca_cola_test = cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Coca-Cola',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        cls.water_test = cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Water',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        cls.minute_maid_test = cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Minute Maid',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        cls.bruschetta = cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 8.50,
            'name': 'Bruschetta',
            'pos_categ_ids': [(4, food_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        cls.wholemeal_loaf = cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.99,
            'name': 'Wholemeal loaf',
            'pos_categ_ids': [(4, breads_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        # multiple categories product
        cls.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Test Multi Category Product',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id), (4, food_category.id)],
            'taxes_id': [(6, 0, [])],
        })

        # desk organizer (variant product)
        cls.desk_organizer = cls.env['product.product'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'pos_categ_ids': [(4, drinks_category.id)],  # will put it as a drink for convenience
        })
        desk_size_attribute = cls.env['product.attribute'].create({
            'name': 'Size',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        desk_size_s = cls.env['product.attribute.value'].create({
            'name': 'S',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_m = cls.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_l = cls.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': desk_size_attribute.id,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_size_attribute.id,
            'value_ids': [(6, 0, [desk_size_s.id, desk_size_m.id, desk_size_l.id])]
        })
        desk_fabrics_attribute = cls.env['product.attribute'].create({
            'name': 'Fabric',
            'display_type': 'select',
            'create_variant': 'no_variant',
        })
        desk_fabrics_leather = cls.env['product.attribute.value'].create({
            'name': 'Leather',
            'attribute_id': desk_fabrics_attribute.id,
        })
        desk_fabrics_other = cls.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': desk_fabrics_attribute.id,
            'is_custom': True,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_fabrics_attribute.id,
            'value_ids': [(6, 0, [desk_fabrics_leather.id, desk_fabrics_other.id])]
        })

        pricelist = cls.env['product.pricelist'].create({'name': 'Restaurant Pricelist'})
        second_pricelist = cls.env['product.pricelist'].create({'name': 'Second Pricelist'})
        cls.pos_config.write({'pricelist_id': pricelist.id})
        cls.pos_config.write({'available_pricelist_ids': [(6, 0, [pricelist.id, second_pricelist.id])]})

        cls.starter_course = cls.env['pos.course'].create({
            'name': 'Test - Starter',
            'category_ids': [(4, drinks_category.id)],
        })

        cls.main_course = cls.env['pos.course'].create({
            'name': 'Test - Main',
            'category_ids': [(4, food_category.id)],
        })


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

    def test_05_tip_screen(self):
        self.pos_config.write({'set_tip_after_payment': True, 'iface_tipproduct': True, 'tip_product_id': self.env.ref('point_of_sale.product_product_tip')})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PosResTipScreenTour')

        orders = self.env['pos.order'].search([], limit=5, order="id desc")
        order_tips = [o.tip_amount for o in orders]

        # orders order can be different depending on which module is install so we sort the tips
        order_tips.sort()
        self.assertEqual(order_tips, [0.0, 0.4, 1.0, 1.0, 1.5])

        order4 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000004')], limit=1, order='id desc')
        self.assertEqual(order4.customer_count, 2)
        self.pos_config.write({
            'preparation_printer_ids': False,
            'other_devices': False,
        })
        self.start_pos_tour('test_edit_payments_with_tip')
        edited_orders = self.env['pos.order'].search([], limit=2)
        # Tip from payment screen - tip should be the part of amount total and amount paid
        payments_order1 = {p.payment_method_id.name: p.amount for p in edited_orders[1].payment_ids}
        self.assertEqual(payments_order1, {'Cash': 6.0, 'Bank': 2.0})
        self.assertEqual(edited_orders[1].amount_total, 8.0)
        self.assertEqual(edited_orders[1].amount_paid, 8.0)
        # verify tip is recorded correctly - should be counted as a part of inclusive and subtotal.
        tip_line_order1 = edited_orders[1].lines.filtered(lambda l: l.product_id == self.env.ref('point_of_sale.product_product_tip'))
        self.assertEqual(tip_line_order1.price_unit, 5.0)
        self.assertEqual(tip_line_order1.price_subtotal, 5.0)
        self.assertEqual(tip_line_order1.price_subtotal_incl, 5.0)

        order5 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000005')], limit=1, order='id desc')
        html = order5.order_receipt_generate_html()
        self.assertTrue(f"Table {order5.table_id.table_number}" in html)
        self.assertTrue("15%" in html)
        self.assertTrue("20%" in html)
        self.assertTrue("25%" in html)

    def test_06_split_bill_screen(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTour2')
        orders = self.env['pos.order'].search([('pos_reference', '!=', '')], limit=2, order='id desc')
        self.assertEqual(len(orders), 2)

    def test_10_save_last_preparation_changes(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SaveLastPreparationChangesTour')
        self.assertTrue(self.pos_config.current_session_id.order_ids.prep_order_ids, "There should be a last order preparation change")
        self.assertTrue(self.coca_cola_test.id == self.pos_config.current_session_id.order_ids.prep_order_ids.prep_line_ids.product_id.id, "The last order preparation change should contain 'Coca'")

    def test_12_order_tracking(self):
        self.pos_config.write({'order_edit_tracking': True})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('OrderTrackingTour')
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-000001')], limit=1, order='id desc')
        self.assertTrue(order1.is_edited)

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

    def test_pos_restaurant_course(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_pos_restaurant_course')
        order = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(order), 1)
        # Verify whether the two courses have different timestamps
        self.assertNotEqual(order.course_ids[0].fired_date, order.course_ids[1].fired_date)

    def test_user_on_residual_order(self):
        self.pos_config.write({'preparation_printer_ids': False})
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
        drinks_category = self.env['pos.category'].search([('name', '=', 'Drinks'), ('sequence', '=', 2)])
        product_1 = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'product_1',
            'taxes_id': self.tax_sale_a,
            'pos_categ_ids': [(4, drinks_category.id)]
        })
        product_2 = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'product_2',
            'taxes_id': self.tax_sale_a,
            'pos_categ_ids': [(4, drinks_category.id)]
        })
        self.pos_config.use_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_tax_in_merge_table_order_line_tour', login="pos_admin")
        line_1 = self.env['pos.order.line'].search([('full_product_name', '=', 'product_1')])
        line_2 = self.env['pos.order.line'].search([('full_product_name', '=', 'product_2')])
        self.assertEqual(line_1.tax_ids, self.tax_sale_a)
        self.assertEqual(line_2.tax_ids, self.tax_sale_a)

    def test_no_ghost_floor(self):
        self.pos_config.use_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('no_ghost_floor', login="pos_admin")

    def test_preset_future_timing_restaurant(self):
        """
        Test to set order preset future date inside a tour
        """
        self.preset_eat_in = self.env['pos.preset'].create({
            'name': 'Eat in',
        })
        self.preset_takeaway = self.env['pos.preset'].create({
            'name': 'Takeaway',
            'identification': 'name',
        })
        self.main_pos_config.write({
            'use_presets': True,
            'default_preset_id': self.preset_eat_in.id,
            'available_preset_ids': [(6, 0, [self.preset_takeaway.id])],
        })
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
                'day_period': 'morning',
            }) for day in range(0, 7)],
        })
        self.preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar
        })
        self.start_pos_tour('test_cancel_future_order', login="pos_user")

    def test_customer_alone_saved(self):
        """
        Tests that when a customer is set, it will be saved and not be reset even if this is the only thing that changed in the order
        """
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'test_customer_alone_saved', login="pos_user")

    def test_no_kitchen_confirmation_for_deposit_money(self):
        if not self.env["ir.module.module"].search([("name", "=", "pos_settle_due"), ("state", "=", "installed")]):
            self.skipTest("pos_settle_due module is required for this test")

        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.pos_config.write({'payment_method_ids': [(4, self.customer_account_payment_method.id)]})
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('test_no_kitchen_confirmation_for_deposit_money', login="pos_admin")

    def test_fast_payment_validation_from_restaurant_product_screen_with_automatic_receipt_printing(self):
        preparation_printer = self.env['pos.printer'].create({
                'name': 'Prep Printer',
                'printer_type': 'epson_epos',
                'printer_ip': '0.0.0.0',
                'use_type': 'preparation',
                'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
            })
        receipt_printer = self.env['pos.printer'].create({
                'name': ' Receipt Printer',
                'printer_type': 'epson_epos',
                'printer_ip': '127.0.0.1',
                'use_type': 'receipt',
            })
        self.main_pos_config.write({
            'use_fast_payment': True,
            'fast_payment_method_ids': [(6, 0, self.bank_payment_method.ids)],
            'use_order_printer': True,
            'preparation_printer_ids': [Command.set([preparation_printer.id])],
            'receipt_printer_ids': [Command.set([receipt_printer.id])],
            'iface_print_auto': True,
            'other_devices': True,
            'preparation_devices': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_fast_payment_validation_from_restaurant_product_screen_with_automatic_receipt_printing')
        order = self.main_pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'paid', "The order should be paid after the fast payment validation")
        self.assertEqual(len(order.payment_ids), 1, "There should be one payment method used for the fast payment")
        self.assertEqual(order.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")

    def test_fast_payment_validation_from_restaurant_product_screen_without_automatic_receipt_printing(self):
        pos_printer = self.env['pos.printer'].create({
                'name': 'Printer',
                'printer_type': 'epson_epos',
                'printer_ip': '0.0.0.0',
                'use_type': 'preparation',
                'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
            })
        self.main_pos_config.write({
            'use_fast_payment': True,
            'fast_payment_method_ids': [(6, 0, self.bank_payment_method.ids)],
            'use_order_printer': True,
            'preparation_printer_ids': [Command.set(pos_printer.ids)],
            'other_devices': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_fast_payment_validation_from_restaurant_product_screen_without_automatic_receipt_printing')
        order = self.main_pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'paid', "The order should be paid after the fast payment validation")
        self.assertEqual(len(order.payment_ids), 1, "There should be one payment method used for the fast payment")
        self.assertEqual(order.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")

    def test_cancel_order_from_ui(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_cancel_order_from_ui')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, "cancel", "The order should be in cancel state")

    def test_sync_lines_qty_update(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_lines_qty_update')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].qty, 3)

    def test_sync_lines_qty_update_ticket_screen(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_lines_qty_update_ticket_screen')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].qty, 3, "Quantity should be updated to 3 in the backend")

    def test_sync_set_partner(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_set_partner')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.partner_id.name, "Acme Corporation")

    def test_sync_set_note(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_set_note')
        order = self.pos_config.current_session_id.order_ids[0]
        note = json.loads(order.internal_note)
        self.assertEqual(note[0]["text"], "Hello world")

    def test_sync_set_line_note(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_set_line_note')
        order = self.pos_config.current_session_id.order_ids[0]
        note = json.loads(order.lines[0].note)
        self.assertEqual(note[0]["text"], "Demo note")

    def test_sync_set_pricelist(self):
        self.pos_config.write({
            'use_pricelist': True,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_sync_set_pricelist')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.pricelist_id.name, "Second Pricelist")

    def test_delete_line_release_table(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_delete_line_release_table')
        order = self.pos_config.current_session_id.order_ids[1]
        # opening a table at end of tour created a draft order
        last_order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(last_order.lines), 0)

    def test_combo_synchronisation(self):
        """This test checks that when a combo line is set as dirty, the parent combo line is also set as dirty.
           if this is not the case, the combo lines would lose their link to the parent combo line and appear as
           normal line"""
        setup_product_combo_items(self)
        self.pos_config.use_order_printer = False
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_combo_synchronisation')

    def test_global_discount_split(self):
        if self.env['ir.module.module']._get('pos_discount').state != 'installed':
            self.skipTest("pos_discount module is required for this test")

        self.discount_product = self.env["product.product"].create({
            "name": "Discount Product",
            "type": "service",
            "list_price": 0,
            "available_in_pos": True,
        })

        self.pos_config.write({
            'iface_discount': True,
            'module_pos_discount': True,
            'discount_product_id': self.discount_product.id,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SplitBillScreenTourTransfer')

    def test_direct_sales(self):
        """
        Direct sales should not be synced without table_id or floating_order_name, if an order is
        sync without one of them, we assign pos_reference in floating_order_name.
        """
        self.start_pos_tour('test_direct_sales', login="pos_user")
        orders = self.env['pos.order'].search([], limit=3, order='id desc')
        self.assertEqual(orders[2].floating_order_name, orders[2].tracking_number)
        self.assertEqual(orders[1].floating_order_name, "Test")
        self.assertEqual(orders[0].floating_order_name, False)
        self.assertIsNotNone(orders[0].table_id)

    def test_future_orders_are_not_cancelled(self):
        """
        This test ensures that a future order is not cancelled when the PoS session is closed.
        """
        self.pos_config.with_user(self.pos_user).open_ui()

        session = self.pos_config.current_session_id
        product = self.env['product.product'].search([('available_in_pos', '=', True)], limit=1)

        present_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product.id,
                'price_unit': 10.0,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10.0,
                'price_subtotal_incl': 10.0,
            })],
            'amount_tax': 0.0,
            'amount_total': 10.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'preset_time': datetime.now(),
        })
        future_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "OL/0002",
                'product_id': product.id,
                'price_unit': 10.0,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10.0,
                'price_subtotal_incl': 10.0,
            })],
            'amount_tax': 0.0,
            'amount_total': 10.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'preset_time': datetime.now() + timedelta(days=1),
        })

        self.start_pos_tour('test_futur_orders_are_not_cancelled')
        self.pos_config.current_session_id.close_session_from_ui()
        self.assertEqual(present_order.state, 'cancel')
        self.assertEqual(future_order.state, 'draft')
        self.assertEqual(future_order.session_id.id, False)

    def test_floating_order_name_change_partner(self):
        # Create partners
        self.env['res.partner'].create([
            {'name': 'Abigael', 'street': '123 Fake St'},
            {'name': 'Deco Addict', 'street': '456 Real St'},
        ])

        # Create presets
        self.preset_eat_in = self.env['pos.preset'].create({
            'name': 'Eat in',
        })
        self.preset_delivery = self.env['pos.preset'].create({
            'name': 'Delivery',
            'identification': 'address',
        })

        self.main_pos_config.write({
            'use_presets': True,
            'default_preset_id': self.preset_eat_in.id,
            'available_preset_ids': [(6, 0, [
                self.preset_eat_in.id,
                self.preset_delivery.id,
            ])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_floating_order_name_change_partner', login="pos_user")

    def test_service_fee(self):
        self.preset_fixed_service_fee = self.env['pos.preset'].create({
            'name': 'Fixed',
            'service_fee': True,
            'service_fee_type': 'fixed',
            'service_fee_amount': 10,
        })
        self.preset_percentage_service_fee_before_discount = self.env['pos.preset'].create({
            'name': 'Percentage before discount',
            'service_fee': True,
            'service_fee_type': 'percent',
            'service_fee_amount': 0.1,
            'service_fee_based_on': 'pre_discount',
        })
        self.preset_percentage_service_fee_after_discount = self.env['pos.preset'].create({
            'name': 'Percentage after discount',
            'service_fee': True,
            'service_fee_type': 'percent',
            'service_fee_amount': 0.1,
            'service_fee_based_on': 'post_discount',
        })

        self.main_pos_config.write({
            'use_presets': True,
            'default_preset_id': self.preset_fixed_service_fee.id,
            'available_preset_ids': [(6, 0, [self.preset_percentage_service_fee_before_discount.id, self.preset_percentage_service_fee_after_discount.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ServiceFeeTour', login="pos_admin")
