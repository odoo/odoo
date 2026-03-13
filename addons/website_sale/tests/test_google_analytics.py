from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGoogleAnalytics(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        attribute = cls.env["product.attribute"].create({
            "name": "Color",
            "sequence": 10,
            "display_type": "color",
            "value_ids": [Command.create({"name": "Red"}), Command.create({"name": "Pink"})],
        })
        cls.env["product.template"].create({
            "name": "Colored T-Shirt",
            "standard_price": 500,
            "list_price": 750,
            "type": "consu",
            "website_published": True,
            "attribute_line_ids": [
                Command.create({"attribute_id": attribute.id, "value_ids": attribute.value_ids})
            ],
        })
        cls.basic_shirt = cls.env["product.template"].create({
            "name": "Basic Shirt",
            "standard_price": 500,
            "list_price": 750,
            "type": "consu",
            "website_published": True,
        })
        cls.env["delivery.carrier"].create({
            "name": "Test Delivery",
            "product_id": cls.env.ref("delivery.product_product_delivery").id,
            "website_published": True,
        })
        cls.env.ref("base.default_website").write({"google_analytics_key": "G-XXXXXXXXXXX"})
        cls.env.ref("base.partner_admin").write({
            "street": "215 Vine St",
            "city": "Scranton",
            "zip": "18503",
            "country_id": cls.env.ref("base.us").id,
            "state_id": cls.env["ir.model.data"]._xmlid_to_res_id("base.state_us_39"),
            "phone": "+1 555-555-5555",
            "email": "admin@yourcompany.example.com",
        })
        if cls.env["ir.module.module"]._get("payment_custom").state == "installed":
            transfer_provider = cls.env.ref("payment.payment_provider_transfer")
            transfer_provider.is_published = True

    def _create_test_cart(self):
        return self.env["sale.order"].create({
            "partner_id": self.env.ref("base.partner_admin").id,
            "website_id": self.env.ref("base.default_website").id,
            "order_line": [
                Command.create({
                    "product_id": self.basic_shirt.product_variant_id.id,
                    "product_uom_qty": 2,
                })
            ],
        })

    def test_view_item(self):
        self.start_tour("/shop?search=Colored T-Shirt", "website_sale.google_analytics_view_item")

    def test_add_to_cart(self):
        self.start_tour("/shop?search=Basic Shirt", "website_sale.google_analytics_add_to_cart")

    def test_select_item(self):
        self.start_tour("/shop?search=Basic Shirt", "website_sale.google_analytics_select_item")

    def test_view_cart(self):
        self._create_test_cart()
        self.start_tour("/shop/cart", "website_sale.google_analytics_view_cart", login="admin")

    def test_begin_checkout(self):
        self._create_test_cart()
        self.start_tour("/shop/cart", "website_sale.google_analytics_begin_checkout", login="admin")

    def test_remove_from_cart(self):
        self._create_test_cart()
        self.start_tour(
            "/shop/cart", "website_sale.google_analytics_remove_from_cart", login="admin"
        )

    def test_add_shipping_info(self):
        self._create_test_cart()
        self.start_tour(
            "/shop/cart", "website_sale.google_analytics_add_shipping_info", login="admin"
        )

    def test_add_to_wishlist(self):
        self.start_tour(
            "/shop?search=Basic Shirt",
            "website_sale.google_analytics_add_to_wishlist",
            login="admin",
        )

    def test_purchase(self):
        if self.env["ir.module.module"]._get("payment_custom").state != "installed":
            self.skipTest("Transfer provider is not installed")
        self._create_test_cart()
        self.start_tour("/shop/cart", "website_sale.google_analytics_purchase", login="admin")
