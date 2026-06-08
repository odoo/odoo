# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

import odoo
from odoo.addons.pos_stock.tests.common import TestPosStockCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosStockProductsWithTax(TestPosStockCommon):

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product1 = self.create_product(
            'Product 1',
            self.categ_basic,
            10.0,
            5.0,
            tax_ids=self.taxes['tax7'].ids,
        )
        self.product2 = self.create_product(
            'Product 2',
            self.categ_basic,
            20.0,
            10.0,
            tax_ids=self.taxes['tax10'].ids,
        )
        self.product3 = self.create_product(
            'Product 3',
            self.categ_basic,
            30.0,
            15.0,
            tax_ids=self.taxes['tax_group_7_10'].ids,
        )
        self.product4 = self.create_product(
            'Product 4',
            self.categ_basic,
            54.99,
            tax_ids=[self.taxes['tax_fixed006'].id, self.taxes['tax_fixed012'].id, self.taxes['tax21'].id],
        )
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_pos_loaded_product_taxes_on_branch(self):
        """ Check loaded product taxes on branch company """
        # create the following branch hierarchy:
        #     Parent company
        #         |----> Branch X
        #                   |----> Branch XX
        company = self.config.company_id
        branch_x = self.env['res.company'].create({
            'name': 'Parent Company',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        branch_xx = self.env['res.company'].create({
            'name': 'Branch XX',
            'country_id': company.country_id.id,
            'parent_id': branch_x.id,
        })
        self.cr.precommit.run()  # load the CoA
        # create taxes for the parent company and its branches
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group',
            'company_id': company.id,
        }, {
            'name': 'Tax Group X',
            'company_id': branch_x.id,
        }, {
            'name': 'Tax Group XX',
            'company_id': branch_xx.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'available_in_pos': True,
            'taxes_id': [],
        })
        # configure a session on Branch XX
        self.xx_bank_journal = self.env['account.journal'].with_company(branch_xx).create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': branch_xx.id,
            'code': 'BNK',
            'sequence': 15,
        })
        xx_config = self.env['pos.config'].with_company(branch_xx).create({
            'name': 'Branch XX config',
            'company_id': branch_xx.id,
        })
        xx_account_receivable = self.company_data['default_account_receivable'].copy({'company_ids': [Command.set(branch_xx.ids)]})
        xx_cash_journal = self.company_data['default_journal_cash'].copy({'company_id': branch_xx.id})
        xx_cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'XX Cash Payment',
            'receivable_account_id': xx_account_receivable.id,
            'journal_id': xx_cash_journal.id,
            'company_id': branch_xx.id,
        })
        xx_config.write({'payment_method_ids': [
            odoo.Command.set(xx_cash_payment_method.ids),
        ]})
        self.config = xx_config
        pos_session = self.open_new_session()
        # load the session data from Branch XX:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        pos_data = pos_session.load_data([])
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_all_taxes.product_tmpl_id.id, pos_data['product.template'])))['taxes_id'],
            tax_xx.ids
        )
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_no_xx_tax.product_tmpl_id.id, pos_data['product.template'])))['taxes_id'],
            tax_x.ids
        )
        tax_data_no_branch = next(iter(filter(lambda p: p['id'] == product_no_branch_tax.product_tmpl_id.id, pos_data['product.template'])))['taxes_id']
        tax_data_no_branch.sort()
        self.assertEqual(
            tax_data_no_branch,
            (tax_a + tax_b).ids
        )
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_no_tax.product_tmpl_id.id, pos_data['product.template'])))['taxes_id'],
            []
        )

        pos_user = self.env['res.users'].create({
            'name': 'Joe Odoo',
            'login': 'pos_user',
            'password': 'pos_user',
            'group_ids': [
                (4, self.env.ref('base.group_user').id),
                (4, self.env.ref('point_of_sale.group_pos_user').id),
                (4, self.env.ref('stock.group_stock_user').id),
            ],
            'tz': 'America/New_York',
            'company_id': branch_xx.id,
            'company_ids': [Command.set([company.id, branch_x.id, branch_xx.id])],
        })

        def get_taxes_name_popup(product):
            product = product.product_tmpl_id
            # In order to simulate the state of the cache when we run this
            # function over RPC, we need to fetch the below data first,
            # invalidate our cache, and then enter `get_product_info_pos`
            # with the arguments already loaded. This is necessary to test
            # an access rights issue when trying to load product info.
            branch_xx_id = branch_xx.id
            xx_config_id = xx_config.id
            product_all_taxes_lst_price = product_all_taxes.lst_price
            self.env.invalidate_all()
            return [tax['name'] for tax in product.with_user(pos_user).with_context(allowed_company_ids=[branch_xx_id]).get_product_info_pos(product_all_taxes_lst_price, 1, xx_config_id)['all_prices']['tax_details']]

        self.assertEqual(get_taxes_name_popup(product_all_taxes), ["Tax XX"])
        self.assertEqual(get_taxes_name_popup(product_no_xx_tax), ["Tax X"])
        self.assertEqual(get_taxes_name_popup(product_no_branch_tax), ["Tax A", "Tax B"])
        self.assertEqual(get_taxes_name_popup(product_no_tax), [])
