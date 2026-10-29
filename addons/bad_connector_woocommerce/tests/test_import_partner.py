from os.path import dirname, join

from vcr import VCR

from odoo.addons.queue_job.tests.common import trap_jobs

from .test_woo_backend import BaseWooTestCase

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures/cassettes"),
    decode_compressed_response=True,
    filter_headers=["Authorization"],
    path_transformer=VCR.ensure_suffix(".yaml"),
    record_mode="once",
)


class TestImportPartner(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Partner."""
        super().setUp()

    def test_import_res_partner(self):
        """Test Assertions for Partner"""
        external_id = "237660088"
        with recorder.use_cassette("import_woo_res_partner"):
            self.env["woo.res.partner"].import_record(
                external_id=external_id, backend=self.backend
            )
        country_record = self.env["res.country"].search([("code", "=", "USA")], limit=1)
        state = self.env["res.country.state"].search(
            [("code", "=", "CA"), ("country_id", "=", country_record.id)],
            limit=1,
        )
        self.partner_model = self.env["woo.res.partner"]
        partner1 = self.partner_model.search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(partner1), 1)
        self.assertTrue(partner1, "Woo Partner is not imported!")
        self.assertEqual(
            partner1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            partner1.firstname,
            "John",
            "Partner's First name is not matched with response!",
        )
        self.assertEqual(
            partner1.lastname,
            "Doe",
            "Partner's Last name is not matched with response!",
        )
        self.assertEqual(
            partner1.name,
            "John Doe",
            "Partner's name is not matched with response!",
        )
        self.assertEqual(
            partner1.email,
            "john.doe@example.com",
            "Partner's Email is not matched with response!",
        )
        self.assertEqual(
            partner1.city,
            "california city",
            "Partner's City is not matched with response!",
        )
        self.assertEqual(
            partner1.country_id.id,
            country_record.id,
            "Partner's Country is not matched with response!",
        )
        self.assertEqual(
            partner1.state_id.id,
            state.id,
            "Partner's State is not matched with response!",
        )

    def test_import_res_partner_batch(self):
        """Test Assertions for Partner"""
        self.backend.force_import_partners = True
        with recorder.use_cassette("import_woo_res_partner"):
            with trap_jobs() as trap:
                self.backend._sync_from_date(
                    model="woo.res.partner",
                    export=False,
                    with_delay=True,
                    force_update_field="force_import_partners",
                )
                # Assert that how many queuejobs are being prepared.
                trap.assert_jobs_count(1)
                # And then skip enqueued jobs
                trap.perform_enqueued_jobs()
