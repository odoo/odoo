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


class TestImportProductTag(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Product Tag."""
        super().setUp()

    def test_import_product_tag(self):
        """Test Assertions for Product Tag"""
        external_id = "35"
        with recorder.use_cassette("import_woo_product_tag"):
            self.env["woo.product.tag"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.product_tag_model = self.env["woo.product.tag"]
        producttag1 = self.product_tag_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(producttag1), 1)
        self.assertTrue(producttag1, "Woo Product Tag is not imported!")
        self.assertEqual(
            producttag1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            producttag1.name,
            "Latest",
            "Product Tag name is not matched with response!",
        )
        self.assertEqual(
            producttag1.slug,
            "latest",
            "slug is not match with response",
        )
        self.assertEqual(
            producttag1.description,
            "latest tag for product.",
            "description is not match with response",
        )
