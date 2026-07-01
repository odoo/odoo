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


class TestImportCountry(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Country."""
        super().setUp()

    def test_import_prices_include_tax_true(self):
        """Test Assertions for Prices Include Tax True"""
        external_id = "woocommerce_prices_include_tax"
        with recorder.use_cassette("import_woo_tax_settings"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(settings1), 1)
        self.assertTrue(settings1, "Woo Country is not imported!")
        self.assertEqual(
            settings1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            settings1.name,
            "Prices entered with tax",
            "Include Tax settings name is not matched with response!",
        )
        self.assertEqual(
            settings1.value,
            "yes",
            "Include Tax settings is not matched with response!",
        )
        self.assertEqual(
            self.backend.include_tax,
            True,
            "Include Tax settings is not matched with response!",
        )

    def test_import_prices_include_tax_false(self):
        """Test Assertions for Prices Include Tax False"""
        external_id = "woocommerce_prices_include_tax"
        with recorder.use_cassette("import_woo_tax_settings_false"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(settings1), 1)
        self.assertTrue(settings1, "Woo Settings is not imported!")
        self.assertEqual(
            settings1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            settings1.name,
            "Prices entered with tax",
            "Include Tax settings name is not matched with response!",
        )
        self.assertEqual(
            settings1.value,
            "no",
            "Include Tax settings is not matched with response!",
        )
        self.assertEqual(
            self.backend.include_tax,
            False,
            "Include Tax settings is not matched with response!",
        )

    def test_import_stock_manage(self):
        """Test Import Stock Manage"""
        external_id = "woocommerce_manage_stock"
        with recorder.use_cassette("import_woo_stock_manage"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [
                ("external_id", "=", external_id),
                ("backend_id", "=", self.backend.id),
            ]
        )
        self.assertEqual(len(settings1), 1)

    def test_import_currency(self):
        """Test Currency"""
        external_id = "woocommerce_currency"
        with recorder.use_cassette("import_woo_currency"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(settings1), 1)

    def test_import_weight(self):
        """Test Weight"""
        external_id = "woocommerce_weight_unit"
        with recorder.use_cassette("import_woo_currency"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(settings1), 1)

    def test_import_dimension(self):
        """Test Dimension"""
        external_id = "woocommerce_dimension_unit"
        with recorder.use_cassette("import_woo_currency"):
            self.env["woo.settings"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.settings_model = self.env["woo.settings"]
        settings1 = self.settings_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(settings1), 1)
