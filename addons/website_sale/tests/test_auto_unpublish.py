# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestAutoUnpublishOutOfStock(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"].create({"group_unpublish_out_of_stock": True}).set_values()

    def test_auto_unpublish_skips_continue_selling_products(self):
        variant = self._create_product(
            is_storable=True, website_id=self.website.id, qty_available=2, is_published=True
        )
        variant.qty_available = 0
        self.assertTrue(variant.product_tmpl_id.is_published)

    def test_auto_unpublish_on_out_of_stock(self):
        variant = self._create_product(
            is_storable=True,
            allow_out_of_stock_order=False,
            website_id=self.website.id,
            qty_available=3,
            is_published=True,
        )
        self.env.invalidate_all()
        variant.qty_available = 0
        self.assertFalse(variant.product_tmpl_id.is_published)

    def test_auto_publish_on_restock(self):
        variant = self._create_product(
            is_storable=True,
            allow_out_of_stock_order=False,
            website_id=self.website.id,
            qty_available=0,
        )
        template = variant.product_tmpl_id
        self.env.invalidate_all()
        variant.qty_available = 5
        self.assertTrue(template.is_published)

    def test_manual_write_overrides_automation(self):
        variant = self._create_product(
            is_storable=True,
            allow_out_of_stock_order=False,
            website_id=self.website.id,
            qty_available=0,
        )
        template = variant.product_tmpl_id
        template.is_published = True
        self.assertTrue(template.is_published)

    def test_stock_update_reenables_automation(self):
        variant = self._create_product(
            is_storable=True,
            allow_out_of_stock_order=False,
            website_id=self.website.id,
            qty_available=5,
        )
        template = variant.product_tmpl_id
        template.is_published = False
        self.env.invalidate_all()
        template.qty_available = 2
        self.assertTrue(template.is_published)
