# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleComboConfigurator(HttpCase, WebsiteSaleCommon):
    def test_website_sale_combo_configurator(self):
        no_variant_attribute = self.env["product.attribute"].create({
            "name": "No variant attribute",
            "create_variant": "no_variant",
            "value_ids": [
                Command.create({"name": "A"}),
                Command.create({"name": "B", "is_custom": True, "default_extra_price": 1}),
            ],
        })
        product_a1 = self.env["product.template"].create({
            "name": "Product A1",
            "website_published": True,
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": no_variant_attribute.id,
                    "value_ids": [Command.set(no_variant_attribute.value_ids.ids)],
                })
            ],
        })
        combo_a = self.env["product.combo"].create({
            "name": "Combo A",
            "combo_item_ids": [
                Command.create({"product_id": product_a1.product_variant_id.id, "extra_price": 5}),
                Command.create({"product_id": self._create_product(name="Product A2").id}),
            ],
        })
        combo_b = self.env["product.combo"].create({
            "name": "Combo B",
            "combo_item_ids": [
                Command.create({"product_id": self._create_product(name="Product B1").id}),
                Command.create({"product_id": self._create_product(name="Product B2").id}),
            ],
        })
        combo_product = self._create_product(
            name="Combo product",
            list_price=25,
            type="combo",
            combo_ids=[Command.link(combo_a.id), Command.link(combo_b.id)],
        )
        self.website.show_line_subtotals_tax_selection = "tax_included"
        self.start_tour(combo_product.website_url, "website_sale.combo_configurator")

    def test_website_sale_combo_configurator_single_configuration(self):
        """Test that the combo configurator isn't shown if there's a single configuration."""
        no_variant_attribute = self.env["product.attribute"].create({
            "name": "No variant attribute",
            "create_variant": "no_variant",
            "value_ids": [Command.create({"name": "A"})],
        })
        product = self.env["product.template"].create({
            "name": "Test product",
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": no_variant_attribute.id,
                    "value_ids": [Command.set(no_variant_attribute.value_ids.ids)],
                })
            ],
            "website_published": True,
        })
        combo = self.env["product.combo"].create({
            "name": "Test combo",
            "combo_item_ids": [Command.create({"product_id": product.product_variant_id.id})],
        })
        combo_product = self._create_product(
            name="Combo product", type="combo", combo_ids=[Command.link(combo.id)]
        )
        self.start_tour(
            combo_product.website_url, "website_sale.combo_configurator_single_configuration"
        )

    def test_website_sale_combo_configurator_single_configurable_item(self):
        """Test that the combo configurator is shown if there's a single combo item, but that combo
        item is configurable.
        """
        no_variant_attribute = self.env["product.attribute"].create({
            "name": "No variant attribute",
            "create_variant": "no_variant",
            "value_ids": [Command.create({"name": "A", "is_custom": True})],
        })
        product = self.env["product.template"].create({
            "name": "Test product",
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": no_variant_attribute.id,
                    "value_ids": [Command.set(no_variant_attribute.value_ids.ids)],
                })
            ],
        })
        combo = self.env["product.combo"].create({
            "name": "Test combo",
            "combo_item_ids": [Command.create({"product_id": product.product_variant_id.id})],
        })
        combo_product = self._create_product(
            name="Combo product", type="combo", combo_ids=[Command.link(combo.id)]
        )
        self.start_tour(
            combo_product.website_url, "website_sale.combo_configurator_single_configurable_item"
        )

    def test_combo_item_tax_included_extra_price(self):
        """Test that combo item extra prices in the website sale configurator include taxes when the
        website is configured to display tax-inclusive prices.
        """
        self.website.show_line_subtotals_tax_selection = "tax_included"
        tax_10 = self.env["account.tax"].create({"name": "Tax 10%", "amount": 10.0})

        product = self._create_product(
            name="Product", list_price=0.0, taxes_id=[Command.link(tax_10.id)]
        )
        combo = self.env["product.combo"].create({
            "name": "Combo choice",
            "combo_item_ids": [Command.create({"product_id": product.id, "extra_price": 10.0})],
        })
        combo_product = self._create_product(
            name="Combo product", list_price=50.0, type="combo", combo_ids=[Command.link(combo.id)]
        )

        result = self.make_jsonrpc_request(
            "/website_sale/combo_configurator/get_data",
            {
                "product_tmpl_id": combo_product.product_tmpl_id.id,
                "quantity": 1,
                "date": datetime(2026, 1, 1).isoformat(),
            },
        )

        combo_item_data = result["combos"][0]["combo_items"][0]
        self.assertAlmostEqual(combo_item_data["extra_price"], 11.0)
