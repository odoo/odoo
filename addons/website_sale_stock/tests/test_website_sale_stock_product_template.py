# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductTemplate(HttpCase, WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_oos_order_allowed = cls._create_product(
            is_storable=True,
            allow_out_of_stock_order=True,
        )
        cls.product_oos_order_not_allowed = cls._create_product(
            is_storable=True,
            allow_out_of_stock_order=False,
        )

    def test_website_sale_stock_get_additional_configurator_data(self):
        product = self.product_oos_order_not_allowed
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 10,
        })

        env = self.env(user=self.public_user)
        with MockRequest(env, website=self.website.with_env(env)):
            configurator_data = self.env['product.template']._get_additional_configurator_data(
                product_or_template=product,
                date=datetime(2000, 1, 1),
                currency=self.currency,
                pricelist=self.pricelist,
            )

        self.assertEqual(configurator_data['free_qty'], 10)

    def test_get_additional_combination_info_max_combo_quantity_with_max(self):
        product_a = self.product_oos_order_not_allowed
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_c = self.product_oos_order_allowed
        self.env['stock.quant'].create([
            {
                'product_id': product_a.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 5,
            }, {
                'product_id': product_b.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 10,
            },
        ])
        combo_a, combo_b, combo_c = self.env['product.combo'].create([
            {'name': "Combo A", 'combo_item_ids': [Command.create({'product_id': product_a.id})]},
            {'name': "Combo B", 'combo_item_ids': [Command.create({'product_id': product_b.id})]},
            {'name': "Combo C", 'combo_item_ids': [Command.create({'product_id': product_c.id})]},
        ])
        combo_product = self._create_product(
            type='combo',
            combo_ids=[
                Command.link(combo_a.id), Command.link(combo_b.id), Command.link(combo_c.id)
            ],
        )
        self.cart.order_line = [Command.create({'product_id': product_a.id, 'product_uom_qty': 3})]

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template'].with_context(
                website_sale_stock_get_quantity=True
            )._get_additionnal_combination_info(
                combo_product,
                quantity=3,
                uom=combo_product.uom_id,
                date=datetime(2000, 1, 1),
                website=self.website
            )

        self.assertEqual(combination_info['max_combo_quantity'], 2)

    def test_get_additional_combination_info_max_combo_quantity_without_max(self):
        product = self.product_oos_order_allowed
        combo = self.env['product.combo'].create({
            'name': "Test combo", 'combo_item_ids': [Command.create({'product_id': product.id})]
        })
        combo_product = self._create_product(type='combo', combo_ids=[Command.link(combo.id)])

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template'].with_context(
                website_sale_stock_get_quantity=True
            )._get_additionnal_combination_info(
                combo_product,
                quantity=3,
                uom=combo_product.uom_id,
                date=datetime(2000, 1, 1),
                website=self.website
            )

        self.assertNotIn('max_combo_quantity', combination_info)

    def test_get_additional_combination_info_free_quantity_is_integer(self):
        self._add_product_qty_to_wh(
            self.product_oos_order_not_allowed.id,
            9,
            self.warehouse.lot_stock_id.id,
        )
        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template'].with_context(
                website_sale_stock_get_quantity=True,
            )._get_additionnal_combination_info(
                self.product_oos_order_not_allowed,
                quantity=9,
                uom=self.env.ref('uom.product_uom_pack_6'),
                date=datetime(2000, 1, 1),
                website=self.website,
            )
        self.assertEqual(combination_info['free_qty'], 1)

    def test_website_show_quick_add_with_variants(self):
        """Quick-add should show for a template with variants even when
        some variants are sold out."""
        size_attribute = self.env["product.attribute"].create({
            "name": "Size",
            "value_ids": [Command.create({"name": "Small"}), Command.create({"name": "Medium"})],
        })
        product_template = self.env["product.template"].create({
            "name": "Test Product With Variants",
            "is_storable": True,
            "allow_out_of_stock_order": False,
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": size_attribute.id,
                    "value_ids": [Command.set(size_attribute.value_ids.ids)],
                })
            ],
        })
        _variant_small, variant_medium = product_template.product_variant_ids
        self._add_product_qty_to_wh(variant_medium.id, 10, self.warehouse.lot_stock_id.id)

        with MockRequest(self.env, website=self.website):
            self.assertTrue(product_template._website_show_quick_add())
