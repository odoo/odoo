# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.tagged('post_install', '-at_install')
class TestFrontend(odoo.tests.HttpCase):
    def test_01_pos_restaurant(self):
        env = self.env(user=self.env.ref('base.user_admin'))
        account_obj = env['account.account']

        pos_config = env.ref('pos_restaurant.pos_config_restaurant')
        main_company = env.ref('base.main_company')

        account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'user_type_id': env.ref('account.data_account_type_receivable').id,
                                                 'reconcile': True})
        field = env['ir.model.fields']._get('res.partner', 'property_account_receivable_id')
        env['ir.property'].create({'name': 'property_account_receivable_id',
                                   'company_id': main_company.id,
                                   'fields_id': field.id,
                                   'value': 'account.account,' + str(account_receivable.id)})
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

        coke = self.env.ref('pos_restaurant.coke')
        coke.write({'taxes_id': [(6, 0, [])]})
        water = self.env.ref('pos_restaurant.water')
        water.write({'taxes_id': [(6, 0, [])]})
        minute_maid = self.env.ref('pos_restaurant.minute_maid')
        minute_maid.write({'taxes_id': [(6, 0, [])]})

        pos_config.open_session_cb()

        self.start_tour("/pos/web?config_id=%d" % pos_config.id, 'pos_restaurant_sync', login="admin")

        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))

        self.start_tour("/pos/web?config_id=%d" % pos_config.id, 'pos_restaurant_sync_second_login', login="admin")

        self.assertEqual(0, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'draft')]))
        self.assertEqual(1, env['pos.order'].search_count([('amount_total', '=', 2.2), ('state', '=', 'draft')]))
        self.assertEqual(2, env['pos.order'].search_count([('amount_total', '=', 4.4), ('state', '=', 'paid')]))
