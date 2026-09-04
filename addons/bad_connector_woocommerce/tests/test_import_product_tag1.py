from os.path import dirname, join

from vcr import VCR

from .test_woo_backend import BaseWooTestCase

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures/cassettes"),
    decode_compressed_response=True,
    filter_headers=["Authorization"],
    path_transformer=VCR.ensure_suffix(".yaml"),
    record_mode="once",
)


class TestImportProductTag1(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Product Tag."""
        super().setUp()

    def test_import_product_tag1(self):
        """Test Assertions for Product Tag which is already present in odoo"""
        external_id = "36"
        producttag = self.env["product.tag"].create({"name": "Old"})
        with recorder.use_cassette("import_woo_product_tag1"):
            self.env["woo.product.tag"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.product_tag_model = self.env["woo.product.tag"]
        producttag2 = self.product_tag_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(producttag2), 1)
        self.assertTrue(producttag2, "Woo Product Tag is not imported!")
        self.assertEqual(
            producttag2.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            producttag2.odoo_id.id,
            producttag.id,
            "Product Tag Id is not Found in Odoo!",
        )
