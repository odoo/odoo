# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_global_discount_tax_group_included(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'none',
            'price_include_override': 'tax_included'
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'none',
            'price_include_override': 'tax_included'
        })
        tax_group_10_20 = self.env['account.tax'].create({
            'name': "tax_group_10_20",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10 + tax_20).ids)],
            'type_tax_use': 'sale',
        })
        self.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 100,
            'taxes_id': [Command.set(tax_group_10_20.ids)],
            'available_in_pos': True,
        })

        self.main_pos_config.module_pos_discount = True
        self.main_pos_config.discount_product_id = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_global_discount_tax_group', login="pos_user")

    def test_global_discount_tax_group_include_exclude(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'none',
            'include_base_amount': True,
            'price_include_override': 'tax_included'
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'none',
        })
        tax_group_10_20 = self.env['account.tax'].create({
            'name': "tax_group_10_20",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10 + tax_20).ids)],
            'type_tax_use': 'sale',
        })
        self.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 100,
            'taxes_id': [Command.set(tax_group_10_20.ids)],
            'available_in_pos': True,
        })

        self.main_pos_config.module_pos_discount = True
        self.main_pos_config.discount_product_id = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_global_discount_tax_group_2', login="pos_user")
