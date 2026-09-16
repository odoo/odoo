from os.path import dirname, join

from vcr import VCR

from odoo import fields

from .test_woo_backend import BaseWooTestCase

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures/cassettes"),
    decode_compressed_response=True,
    filter_headers=["Authorization"],
    path_transformer=VCR.ensure_suffix(".yaml"),
    record_mode="once",
)


class TestImportProduct(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Product."""
        super().setUp()

    def test_import_product_product(self):
        """Test Assertions for Product"""
        external_id = "50"
        quantity_to_add = 10
        quantity_to_add_1 = 5
        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.product.product"].import_record(
                external_id=external_id, backend=self.backend
            )
        product1 = self.env["woo.product.product"].search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)],
            limit=1,
        )
        self.assertTrue(product1, "Woo Product is not imported!")
        self.assertEqual(
            product1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            product1.name,
            "Shirt",
            "Product's name is not matched with response!",
        )
        self.assertEqual(
            product1.purchase_ok,
            False,
            "Purchase is not matched with response!",
        )
        self.assertEqual(
            product1.list_price,
            500,
            "List Price is not matched with response",
        )
        self.assertEqual(
            product1.default_code,
            "shirt-sku",
            "default_code is not match with response",
        )
        self.assertEqual(
            product1.price,
            "500",
            "Price is not matched with response",
        )
        self.assertEqual(
            product1.description,
            "<p>shirt.</p>\n",
            "description is not matched with response",
        )
        self.assertEqual(
            product1.regular_price,
            "599",
            "regular price is not matched with response",
        )
        self.assertEqual(
            product1.status,
            "publish",
            "status is not matched with response",
        )
        self.assertEqual(
            product1.tax_status,
            "taxable",
            "tax status is not matched with response",
        )
        self.assertEqual(
            product1.stock_status,
            "instock",
            "stock status is not matched with response",
        )
        self.assertEqual(
            product1.detailed_type,
            "product",
            "Product Type is not matched with response",
        )
        self.assertTrue(
            product1.stock_management,
            "Stock Management is not matched with response",
        )
        self.assertEqual(
            product1.woo_product_qty,
            2000,
            "Product Quantity is not matched with response",
        )
        self.assertEqual(
            product1.detailed_type,
            self.backend.default_product_type,
            "Product Type is not matched with response.",
        )
        product2 = self.env["product.product"].search(
            [("woo_bind_ids.external_id", "=", external_id)], limit=1
        )
        stock_quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": product2.id,
                    "inventory_quantity": quantity_to_add,
                    "location_id": self.backend.stock_inventory_warehouse_ids[
                        0
                    ].lot_stock_id.id,
                }
            )
        )
        stock_quant.action_apply_inventory()
        stock_quant_1 = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": product2.id,
                    "inventory_quantity": quantity_to_add_1,
                    "location_id": self.backend.stock_inventory_warehouse_ids[
                        1
                    ].lot_stock_id.id,
                }
            )
        )
        stock_quant_1.action_apply_inventory()
        with recorder.use_cassette("export_stock_qty"):
            product2.update_stock_qty()
        self.assertEqual(
            product2.woo_bind_ids.woo_product_qty,
            15,
            "Product is Not Exported in WooCommerce.",
        )

    def test_import_product_product_variant_type(self):
        """Test Assertions for Varaint type Product"""
        external_id = "162"
        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.product.product"].import_record(
                external_id=external_id, backend=self.backend
            )
        product1 = self.env["woo.product.product"].search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)],
            limit=1,
        )
        self.assertTrue(product1, "Woo Product is not imported!")
        self.assertEqual(
            product1.detailed_type,
            "product",
            "Product Quantity is not matched with response",
        )

    def test_import_product_template(self):
        """Test Assertions for Product Template"""
        external_id = "130"
        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.product.template"].import_record(
                external_id=external_id, backend=self.backend
            )
        product1 = self.env["woo.product.template"].search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)],
            limit=1,
        )
        self.assertTrue(product1, "Woo Product is not imported!")
        product1.write({"sync_date": fields.Datetime.now()})
        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.product.template"].import_record(
                external_id=product1.external_id, backend=self.backend
            )

    def test_downloadable_product(self):
        """Test Assertions for Downloadable Product"""
        external_id = "90"
        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.product.product"].import_record(
                external_id=external_id, backend=self.backend
            )
        product1 = self.env["woo.product.product"].search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)],
            limit=1,
        )
        self.assertTrue(product1, "Woo Product is not imported!")
        self.assertEqual(
            product1.detailed_type,
            "service",
            "Product type is not matched with response",
        )
