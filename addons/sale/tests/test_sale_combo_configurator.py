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

    def test_sale_combo_configurator_preselect_single_unconfigurable_items(self):
        if self.env['ir.module.module']._get('sale_management').state != 'installed':
            self.skipTest("Sale App is not installed, Sale menu is not accessible.")

        unconfigurable_no_variant_attribute = self.env['product.attribute'].create({
            'name': "Attribute A",
            'create_variant': 'no_variant',
            'value_ids': [Command.create({'name': "A"})],
        })
        configurable_no_variant_attribute = self.env['product.attribute'].create({
            'name': "Attribute B",
            'create_variant': 'no_variant',
            'display_type': 'multi',
            'value_ids': [Command.create({'name': "B"})],
        })
        unconfigurable_always_attribute = self.env['product.attribute'].create({
            'name': "Attribute C",
            'create_variant': 'always',
            'value_ids': [Command.create({'name': "C"})],
        })
        configurable_always_attribute = self.env['product.attribute'].create({
            'name': "Attribute D",
            'create_variant': 'always',
            'value_ids': [Command.create({'name': "D", 'is_custom': True})],
        })
        unconfigurable_no_variant_combo = self._create_combo_from_attribute(
            unconfigurable_no_variant_attribute, "Product A", "Combo A"
        )
        configurable_no_variant_combo = self._create_combo_from_attribute(
            configurable_no_variant_attribute, "Product B", "Combo B"
        )
        unconfigurable_always_combo = self._create_combo_from_attribute(
            unconfigurable_always_attribute, "Product C", "Combo C"
        )
        configurable_always_combo = self._create_combo_from_attribute(
            configurable_always_attribute, "Product D", "Combo D"
        )
        combo_with_multiple_unconfigurable_items = self.env['product.combo'].create({
            'name': "Combo E",
            'combo_item_ids': [
                Command.create({'product_id': self._create_product(name="Product E1").id}),
                Command.create({'product_id': self._create_product(name="Product E2").id}),
            ],
        })
        self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[
                Command.link(unconfigurable_no_variant_combo.id),
                Command.link(configurable_no_variant_combo.id),
                Command.link(unconfigurable_always_combo.id),
                Command.link(configurable_always_combo.id),
                Command.link(combo_with_multiple_unconfigurable_items.id),
            ],
        )
        self.start_tour(
            '/', 'sale_combo_configurator_preselect_single_unconfigurable_items', login='salesman'
        )

    def test_sale_combo_configurator_preconfigure_unconfigurable_ptals(self):
        if self.env['ir.module.module']._get('sale_management').state != 'installed':
            self.skipTest("Sale App is not installed, Sale menu is not accessible.")

        unconfigurable_no_variant_attribute = self.env['product.attribute'].create({
            'name': "Attribute A",
            'create_variant': 'no_variant',
            'value_ids': [Command.create({'name': "A"})],
        })
        configurable_no_variant_attribute = self.env['product.attribute'].create({
            'name': "Attribute B",
            'create_variant': 'no_variant',
            'display_type': 'multi',
            'value_ids': [Command.create({'name': "B"})],
        })
        product = self.env['product.template'].create({
            'name': "Test product",
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': unconfigurable_no_variant_attribute.id,
                    'value_ids': [Command.set(unconfigurable_no_variant_attribute.value_ids.ids)],
                }),
                Command.create({
                    'attribute_id': configurable_no_variant_attribute.id,
                    'value_ids': [Command.set(configurable_no_variant_attribute.value_ids.ids)],
                }),
            ],
        })
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [Command.create({'product_id': product.product_variant_id.id})],
        })
        self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[Command.link(combo.id)],
        )
        self.start_tour(
            '/', 'sale_combo_configurator_preconfigure_unconfigurable_ptals', login='salesman'
        )

    def _create_combo_from_attribute(self, attribute, product_name, combo_name):
        product = self.env['product.template'].create({
            'name': product_name,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)],
                }),
            ],
        })
        return self.env['product.combo'].create({
            'name': combo_name,
            'combo_item_ids': [Command.create({'product_id': product.product_variant_id.id})],
        })
