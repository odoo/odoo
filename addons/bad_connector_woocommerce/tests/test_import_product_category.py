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


class TestImportProductCategory(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Product Category."""
        super().setUp()

    def test_import_product_category(self):
        """Test Assertions for Product Category"""
        external_id = "1374"
        with recorder.use_cassette("import_woo_product_category"):
            self.env["woo.product.category"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.product_model = self.env["woo.product.category"]
        productcategory1 = self.product_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(productcategory1), 1)
        self.assertTrue(productcategory1, "Woo Product Category is not imported!")
        self.assertEqual(
            productcategory1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            productcategory1.name,
            "Men",
            "Product Category name is not matched with response!",
        )
        self.assertEqual(
            productcategory1.slug,
            "men",
            "Slug is not matched with response",
        )
        self.assertEqual(
            productcategory1.display,
            "default",
            "Display is not matched with response",
        )
        self.assertEqual(
            productcategory1.count,
            4,
            "Count is not match with response",
        )
