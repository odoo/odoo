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


class TestImportPaymentGateway(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Payment Gateway."""
        super().setUp()

    def test_import_payment_gateway(self):
        """Test Assertions for Payment Gateway"""
        external_id = "bacs"
        with recorder.use_cassette("import_payment_gateway"):
            self.env["woo.payment.gateway"].import_record(
                external_id=external_id, backend=self.backend
            )
        self.payment_model = self.env["woo.payment.gateway"]
        payment1 = self.payment_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(payment1), 1)
        self.assertTrue(payment1, "Woo Country is not imported!")
        self.assertEqual(
            payment1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            payment1.name,
            "Direct bank transfer",
            "Payment name is not matched with response!",
        )
        self.assertEqual(
            payment1.slug,
            "Make your payment directly into our bank account.",
            "Payment slug is not matched with response!",
        )
        self.assertTrue(payment1.enable, "Payment should be enabled")
        self.assertEqual(
            payment1.description,
            "Take payments in person via BACS.",
            "Country description is not matched with response!",
        )
