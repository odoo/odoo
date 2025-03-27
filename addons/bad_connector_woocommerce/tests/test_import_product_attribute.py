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


class TestImportProductAttributes(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Product Attribute."""
        super().setUp()

    def test_import_product_attribute(self):
        """Test Assertions for Product Attribute"""
        external_id = "2"
        with recorder.use_cassette("import_woo_product_attribute"):
            self.env["woo.product.attribute"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.product_model = self.env["woo.product.attribute"]
        productattribute1 = self.product_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(productattribute1), 1)
        self.assertTrue(productattribute1, "Woo Product Attribute is not imported!")
        self.assertEqual(
            productattribute1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            productattribute1.name,
            "colour",
            "Product Attribute name is not matched with response!",
        )
        self.assertEqual(
            productattribute1.has_archives,
            False,
            "has_archives is not match with response",
        )
        productattribute1.odoo_id.import_product_attribute_value()
