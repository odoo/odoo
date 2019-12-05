# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.tagged('post_install', '-at_install')
class TestFrontend(odoo.tests.HttpCase):
    def test_01_pos_restaurant(self):
        env = self.env(user=self.env.ref('base.user_admin'))
        account_obj = env['account.account']

        printer = self.env['restaurant.printer'].create({
            'name': 'Kitchen Printer',
            'proxy_ip': 'localhost',
        })
        drinks_category = self.env['pos.category'].create({'name': 'Drinks'})

        pos_config = self.env['pos.config'].create({
            'name': 'Bar',
            'barcode_nomenclature_id': self.env.ref('barcodes.default_barcode_nomenclature').id,
            'module_pos_restaurant': True,
            'is_table_management': True,
            'iface_splitbill': True,
            'iface_printbill': True,
            'iface_orderline_notes': True,
            'printer_ids': [(4, printer.id)],
            'iface_start_categ_id': drinks_category.id,
            'start_category': True,
            'pricelist_id': self.env.ref('product.list0').id,
        })

        main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_id': pos_config.id,
        })

        table_05 = self.env['restaurant.table'].create({
            'name': 'T5',
            'floor_id': main_floor.id,
            'seats': 4,
        })
        table_04 = self.env['restaurant.table'].create({
            'name': 'T4',
            'floor_id': main_floor.id,
            'seats': 4,
        })
        table_02 = self.env['restaurant.table'].create({
            'name': 'T2',
            'floor_id': main_floor.id,
            'seats': 4,
        })

        main_company = env.ref('base.main_company')

        account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'user_type_id': env.ref('account.data_account_type_receivable').id,
                                                 'reconcile': True})

        self.env['ir.property'].set_default(
            'property_account_receivable_id',
            'res.partner',
            account_receivable,
            main_company,
        )

        test_sale_journal = env['account.journal'].create({
            'name': 'Sales Journal - Test',
            'code': 'TSJ',
            'type': 'sale',
            'company_id': main_company.id
            })

        cash_journal = env['account.journal'].create({
            'name': 'Cash Test',
            'code': 'TCJ',
            'type': 'sale',
            'company_id': main_company.id
            })

        pos_config.write({
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'payment_method_ids': [(0, 0, {
                'name': 'Cash restaurant',
                'split_transactions': True,
                'receivable_account_id': account_receivable.id,
                'is_cash_count': True,
                'cash_journal_id': cash_journal.id,
            })],
        })

        coke = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Coca-Cola',
            'weight': 0.01,
            'pos_categ_id': drinks_category.id,
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        water = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Water',
            'weight': 0.01,
            'pos_categ_id': drinks_category.id,
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        minute_maid = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 2.20,
            'name': 'Minute Maid',
            'weight': 0.01,
            'pos_categ_id': drinks_category.id,
            'categ_id': self.env.ref('point_of_sale.product_category_pos').id,
            'taxes_id': [(6, 0, [])],
        })

        pos_config.with_user(self.env.ref('base.user_admin')).open_session_cb(check_coa=False)

        self.start_tour("/pos/web?config_id=%d" % pos_config.id, 'pos_restaurant_sync', login="admin")

        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

        self.start_tour("/pos/web?config_id=%d" % pos_config.id, 'pos_restaurant_sync_second_login', login="admin")

        self.assertEqual(0, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 2.2), ('state', '=', 'draft')]))
        self.assertEqual(2, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))
