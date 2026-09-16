from odoo.addons.document_compliance.tests.common import ComplianceCase


class TestComplianceReportAssets(ComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["document.type"].search([("is_mandatory", "=", True)]).write(
            {"is_mandatory": False}
        )
        cls.asset_type = cls._type(
            "SCOPE_ASSET", is_mandatory=True, applies_to="resource.asset"
        )
        cls.partner_type = cls._type(
            "SCOPE_PARTNER_ONLY", is_mandatory=True, applies_to="res.partner"
        )
        cls.asset = cls.env["resource.asset"].create(
            {
                "name": "Reported Asset",
                "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
            }
        )

    def test_assets_are_an_entity_a_type_can_apply_to(self):
        selection = dict(self.env["document.type"]._selection_applies_to())

        self.assertIn("resource.asset", selection)

    def _report_row(self):
        return self.env["document.compliance.report"].search(
            [("entity_type", "=", "resource.asset"), ("entity_id", "=", self.asset.id)]
        )

    def test_an_asset_is_held_only_to_asset_types(self):
        self._doc(
            self.asset_type,
            365,
            name="Insurance Policy",
            res_model="resource.asset",
            res_id=self.asset.id,
        )
        self._publish()

        row = self._report_row()

        self.assertEqual(row.entity_name, "Reported Asset")
        self.assertEqual((row.total_required, row.total_valid), (1, 1))
        self.assertEqual(row.compliance_state, "compliant")

    def test_an_asset_missing_its_paper_is_reported(self):
        self._publish()

        row = self._report_row()

        self.assertEqual((row.total_required, row.total_valid), (1, 0))
        self.assertNotEqual(row.compliance_state, "compliant")

    def test_an_expired_paper_does_not_count_as_valid(self):
        self._doc(
            self.asset_type,
            -1,
            name="Lapsed Policy",
            res_model="resource.asset",
            res_id=self.asset.id,
        )
        self._publish()

        row = self._report_row()

        self.assertEqual((row.total_required, row.total_valid), (1, 0))
