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


class TestImportWooTax(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for WooCommerce Tax."""
        super().setUp()

    def test_import_woo_tax(self):
        """Test Assertions for WooCommerce Tax"""
        external_id = "1"
        tax_name = "Tax 19%"
        tax_amount = 19.0000
        tax_record = self.env["account.tax"].create(
            {
                "name": tax_name,
                "amount": tax_amount,
            }
        )
        with recorder.use_cassette("import_woo_tax"):
            self.env["woo.tax"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.tax_model = self.env["woo.tax"]
        tax1 = self.tax_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(tax1), 1)
        self.assertTrue(tax1, "WooCommerce Tax is not imported!")
        self.assertEqual(tax1.external_id, external_id, "External ID is different!!")
        self.assertEqual(
            tax1.name,
            "Tax 19.0%",
            "Tax name is not matched with response!",
        )
        self.assertEqual(
            tax1.woo_amount,
            19.0,
            "WooCommerce Ammount is not matched with response",
        )
        self.assertEqual(tax1.odoo_id.id, tax_record.id, "Odoo Id is not found in Odoo")
