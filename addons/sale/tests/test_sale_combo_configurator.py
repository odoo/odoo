# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleComboConfigurator(HttpCase, SaleCommon):

    def test_sale_combo_configurator(self):
        if self.env['ir.module.module']._get('sale_management').state != 'installed':
            self.skipTest("Sale App is not installed, Sale menu is not accessible.")

        no_variant_attribute = self.env['product.attribute'].create({
            'name': "No variant attribute",
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': "A"}),
                Command.create({'name': "B", 'is_custom': True, 'default_extra_price': 1}),
            ],
        })
        product_a1 = self.env['product.template'].create({
            'name': "Product A1",
            'list_price': 100,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': no_variant_attribute.id,
                    'value_ids': [Command.set(no_variant_attribute.value_ids.ids)],
                }),
            ],
        })
        combo_a = self.env['product.combo'].create({
            'name': "Combo A",
            'combo_item_ids': [
                Command.create({'product_id': product_a1.product_variant_id.id, 'extra_price': 5}),
                Command.create({'product_id': self._create_product(name="Product A2").id}),
            ],
        })
        combo_b = self.env['product.combo'].create({
            'name': "Combo B",
            'combo_item_ids': [
                Command.create({'product_id': self._create_product(name="Product B1").id}),
                Command.create({'product_id': self._create_product(name="Product B2").id}),
            ],
        })
        self._create_product(
            name="Combo product",
            list_price=25,
            type='combo',
            combo_ids=[
                Command.link(combo_a.id),
                Command.link(combo_b.id),
            ],
        )
        self.start_tour('/', 'sale_combo_configurator', login='salesman')
