# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_pos_combo_items

@odoo.tests.tagged('post_install', '-at_install')
class TestFrontend(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.env.ref('base.user_admin'))
        self.env.ref('base.user_demo').write({
            'groups_id': [(4, self.env.ref('point_of_sale.group_pos_manager').id)],
        })

        account_obj = self.env['account.account']

        account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'account_type': 'asset_receivable',
                                                 'reconcile': True})

        drinks_category = self.env['pos.category'].create({'name': 'Drinks'})

        printer = self.env['pos.printer'].create({
            'name': 'Preparation Printer',
            'epson_printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [drinks_category.id]
        })

        main_company = self.env.ref('base.main_company')

        second_cash_journal = self.env['account.journal'].create({
            'name': 'Cash 2',
            'type': 'cash',
            'company_id': main_company.id
            })

        self.env['pos.payment.method'].create({
            'name': 'Cash 2',
            'split_transactions': False,
            'receivable_account_id': account_receivable.id,
            'journal_id': second_cash_journal.id,
        })

        pos_config = self.env['pos.config'].create({
            'name': 'Bar',
            'module_pos_restaurant': True,
            'iface_splitbill': True,
            'iface_printbill': True,
            'iface_orderline_notes': True,
            'iface_start_categ_id': drinks_category.id,
            'start_category': True,
            'is_order_printer': True,
            'printer_ids': [(4, printer.id)],
            'iface_tipproduct': False,
        })
        pos_config.floor_ids.unlink()

        main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, pos_config.id)],
        })

        table_05 = self.env['restaurant.table'].create({
            'name': '5',
            'floor_id': main_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 100,
        })
        table_04 = self.env['restaurant.table'].create({
            'name': '4',
            'floor_id': main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 150,
            'position_v': 100,
        })
        table_02 = self.env['restaurant.table'].create({
            'name': '2',
            'floor_id': main_floor.id,
            'seats': 4,
            'position_h': 250,
            'position_v': 100,
        })

        second_floor = self.env['restaurant.floor'].create({
            'name': 'Second Floor',
            'pos_config_ids': [(4, pos_config.id)],
        })

        table_01 = self.env['restaurant.table'].create({
            'name': '1',
            'floor_id': second_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 100,
            'position_v': 150,
        })
        table_03 = self.env['restaurant.table'].create({
            'name': '3',
            'floor_id': second_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 250,
        })

        self.env['ir.property']._set_default(
            'property_account_receivable_id',
            'res.partner',
            account_receivable,
            main_company,
        )

        test_sale_journal = self.env['account.journal'].create({
            'name': 'Sales Journal - Test',
            'code': 'TSJ',
            'type': 'sale',
            'company_id': main_company.id
            })

        cash_journal = self.env['account.journal'].create({
            'name': 'Cash Test',
            'code': 'TCJ',
            'type': 'cash',
            'company_id': main_company.id
            })

        pos_config.write({
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'payment_method_ids': [(0, 0, {
                'name': 'Cash',
                'split_transactions': False,
                'receivable_account_id': account_receivable.id,
                'journal_id': cash_journal.id,
            })],
        })

        coke = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Coca-Cola',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        water = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Water',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        minute_maid = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Minute Maid',
            'weight': 0.01,
            'pos_categ_ids': [(4, drinks_category.id)],
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        pricelist = self.env['product.pricelist'].create({'name': 'Restaurant Pricelist'})
        pos_config.write({'pricelist_id': pricelist.id})

        self.pos_config = pos_config

    def test_01_pos_restaurant(self):

        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'pos_restaurant_sync', login="demo")

        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'pos_restaurant_sync_second_login', login="demo")

        self.assertEqual(0, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, self.env['pos.order'].search_count([('amount_total', '=', 2.2), ('state', '=', 'draft')]))
        self.assertEqual(2, self.env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

    def test_02_others(self):
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'SplitBillScreenTour', login="demo")
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'ControlButtonsTour', login="demo")
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'FloorScreenTour', login="demo")

    def test_04_ticket_screen(self):
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'PosResTicketScreenTour', login="demo")

    def test_05_tip_screen(self):
        self.pos_config.write({'set_tip_after_payment': True, 'iface_tipproduct': True, 'tip_product_id': self.env.ref('point_of_sale.product_product_tip')})
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'PosResTipScreenTour', login="demo")

        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1, order='id desc')
        order2 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0002')], limit=1, order='id desc')
        order3 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0003')], limit=1, order='id desc')
        order4 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0004')], limit=1, order='id desc')
        order5 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0005')], limit=1, order='id desc')

        self.assertTrue(order1.is_tipped and order1.tip_amount == 0.40)
        self.assertTrue(order2.is_tipped and order2.tip_amount == 1.00)
        self.assertTrue(order3.is_tipped and order3.tip_amount == 1.50)
        self.assertTrue(order4.is_tipped and order4.tip_amount == 1.00)
        self.assertTrue(order5.is_tipped and order5.tip_amount == 0.00)

    def test_06_split_bill_screen(self):
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'SplitBillScreenTour2', login="demo")

    def test_07_split_bill_screen(self):
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'SplitBillScreenTour3', login="demo")

    def test_08_refund_stay_current_table(self):
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'RefundStayCurrentTableTour', login="demo")

    def test_09_combo_split_bill(self):
        combo_product = setup_pos_combo_items(self)
        combo_product.write({'lst_price': 40})
        self.pos_config.with_user(self.env.ref('base.user_demo')).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.pos_config.id}", 'SplitBillScreenTour4PosCombo', login="demo")
