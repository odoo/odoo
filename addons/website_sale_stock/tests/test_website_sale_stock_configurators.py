# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockConfigurators(HttpCase, WebsiteSaleStockCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    def test_website_sale_stock_combo_configurator(self):
        product = self._create_product(name="Test product")
        self.env["stock.quant"].sudo().create({
            "product_id": product.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "quantity": 2,
        })
        combo = self.env["product.combo"].create({
            "name": "Test combo",
            "combo_item_ids": [
                Command.create({"product_id": product.id}),
                Command.create({
                    "product_id": self._create_product(
                        allow_out_of_stock_order=True, is_storable=False
                    ).id
                }),
            ],
        })
        product = self._create_product(
            name="Combo product", type="combo", combo_ids=[Command.link(combo.id)]
        )
        self.start_tour(product.website_url, "website_sale_stock.combo_configurator")
