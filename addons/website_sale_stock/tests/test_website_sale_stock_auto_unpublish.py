# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestAutoUnpublishOutOfStock(WebsiteSaleStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website.warehouse_id = cls.warehouse
        cls.website.website_sale_unpublish_out_of_stock = True

    def _create_published_storable(self, qty=0):
        """Return a published storable product with allow_out_of_stock_order=False."""
        variant = self._create_product(
            is_storable=True, allow_out_of_stock_order=False, website_published=True
        )
        template = variant.product_tmpl_id
        if qty:
            self._add_product_qty_to_wh(variant.id, qty, self.warehouse.lot_stock_id.id)
        return template

    def _add_stock(self, template, qty):
        self._add_product_qty_to_wh(
            template.product_variant_id.id, qty, self.warehouse.lot_stock_id.id
        )

    def test_auto_republish_when_stock_restored(self):
        """Product unpublished due to OOS must republish when stock is added."""
        template = self._create_published_storable(qty=0)
        template._sync_website_published_state()
        self.assertFalse(template.is_published)
        self._add_stock(template, 5)
        self.assertTrue(template.is_published)
        self.assertFalse(template.auto_unpublished_date)

    def test_no_re_unpublish_when_merchant_manually_republished(self):
        """Merchant republishing while OOS must prevent the system from unpublishing again."""
        template = self._create_published_storable(qty=0)
        template._sync_website_published_state()
        self.assertTrue(template.auto_unpublished_date)
        template.write({"is_published": True})
        template._sync_website_published_state()
        self.assertTrue(template.is_published)

    def test_allow_out_of_stock_order_republishes_auto_unpublished(self):
        """Enabling Continue Selling on an auto-unpublished product must republish it."""
        template = self._create_published_storable(qty=0)
        template._sync_website_published_state()
        self.assertTrue(template.auto_unpublished_date)
        template.write({"allow_out_of_stock_order": True})
        self.assertTrue(template.is_published)
        self.assertFalse(template.auto_unpublished_date)

    def test_retroactive_unpublish_on_setting_enable(self):
        """Enabling the website setting must immediately unpublish existing OOS products."""
        self.website.website_sale_unpublish_out_of_stock = False
        template = self._create_published_storable(qty=0)
        self.assertTrue(template.is_published)
        self.website.website_sale_unpublish_out_of_stock = True
        self.assertFalse(template.is_published)
        self.assertTrue(template.auto_unpublished_date)
