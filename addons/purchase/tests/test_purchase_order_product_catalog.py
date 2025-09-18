
from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestPurchaseOrderProductCatalog(HttpCase):

    def test_add_section_from_product_catalog_on_purchase_order_tour(self):
        vendor = self.env["res.partner"].create({"name": "Test Vendor"})
        self.env["product.template"].create(
            {
                "name": "Test Product",
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": vendor.id,
                            "min_qty": 1.0,
                            "price": 1.0,
                        },
                    )
                ],
            }
        )
        self.start_tour(
            "/web#action=purchase.action_purchase_order",
            "test_add_section_from_product_catalog_on_purchase_order",
            login="admin",
        )
