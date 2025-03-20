# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo import Command


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'none',
        })
        self.tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'none',
        })
        self.tax_group_10_20 = self.env['account.tax'].create({
            'name': "tax_group_10_20",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((self.tax_10 + self.tax_20).ids)],
            'type_tax_use': 'sale',
        })
        self.product_awesome_item.write({
            'taxes_id': [Command.set(self.tax_group_10_20.ids)],
            'list_price': 100
        })
        self.pos_config.module_pos_discount = True
        self.pos_config.discount_product_id = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)

    def test_global_discount_tax_group_included(self):
        self.tax_10.write({
            'price_include_override': 'tax_included'
        })
        self.tax_20.write({
            'price_include_override': 'tax_included'
        })
        self.start_pos_tour('pos_global_discount_tax_group')

    def test_global_discount_tax_group_include_exclude(self):
        self.tax_10.write({
            'include_base_amount': True,
            'price_include_override': 'tax_included'
        })
        self.start_pos_tour('pos_global_discount_tax_group_2')
