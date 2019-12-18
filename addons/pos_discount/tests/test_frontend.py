# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, timedelta

from odoo.tests import tagged, HttpCase

@tagged('post_install', '-at_install')
class TestUi(HttpCase):
    def test_global_discount(self):
        env = self.env(user=self.env.ref('base.user_admin'))
        journal_obj = env['account.journal']
        account_obj = env['account.account']

        self.main_company = env.ref('base.main_company')
        # set the company currency to USD, otherwise it will assume
        # euro's. this will cause issues as the sales journal is in
        # USD, because of this all products would have a different
        # price
        self.main_company.currency_id = env.ref('base.USD')

        self.main_pos_config = env.ref('point_of_sale.pos_config_main')

        self.account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'user_type_id': env.ref('account.data_account_type_receivable').id,
                                                 'reconcile': True})
        field = env['ir.model.fields']._get('res.partner', 'property_account_receivable_id')
        env['ir.property'].create({'name': 'property_account_receivable_id',
                                   'company_id': self.main_company.id,
                                   'fields_id': field.id,
                                   'value': 'account.account,' + str(self.account_receivable.id)})

        cash_journal = journal_obj.create({
            'name': 'Cash Test',
            'type': 'cash',
            'company_id': self.main_company.id,
            'code': 'CSH',
            'sequence': 10,
        })

        test_sale_journal = journal_obj.create({'name': 'Sales Journal - Test',
                                                'code': 'TSJ',
                                                'type': 'sale',
                                                'company_id': self.main_company.id})

        # needed because tests are run before the module is marked as
        # installed. In js web will only load qweb coming from modules
        # that are returned by the backend in module_boot. Without
        # this you end up with js, css but no qweb.
        env['ir.module.module'].search([('name', '=', 'point_of_sale')], limit=1).state = 'installed'
        env['ir.module.module'].search([('name', '=', 'pos_discount')], limit=1).state = 'installed'
        
        discount_product = self.env['product.product'].create({
                    'sale_ok': False,
                    'purchase_ok': False,
                    'name': 'Discount',
                    'default_code': 'DISC',
                    'list_price': 0.0,
                    'type': 'consu',
                    'to_weight': False,
                    'taxes_id': [],
                    'barcode': '123456',
                    })

        self.main_pos_config.write({
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'payment_method_ids': [(0, 0, { 'name': 'Cash',
                                            'is_cash_count': True,
                                            'cash_journal_id': cash_journal.id,
                                            'receivable_account_id': self.account_receivable.id,
            })],
            'module_pos_discount': True,
            'discount_product_id': discount_product.id
        })
        
        
        tax_10 = env['account.tax'].create({'name': "10", 'amount': 10})
        tax_15 = env['account.tax'].create({'name': "15", 'amount': 15})

        # Todo
        env['product.product'].search([('name', '=', 'Acoustic Bloc Screens')], limit=1).taxes_id = [(6, 0, [tax_15.id])]
        env['product.product'].search([('name', '=', 'Monitor Stand')], limit=1).taxes_id = [(6, 0, [tax_10.id])]

        # open a session, the /pos/web controller will redirect to it
        self.main_pos_config.open_session_cb()

        self.start_tour("/pos/web?debug=1&config_id=%d" % self.main_pos_config.id, 'pos_discount_global_discount', login="admin")
