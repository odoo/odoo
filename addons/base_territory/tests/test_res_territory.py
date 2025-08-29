from odoo.tests.common import TransactionCase


class TestResTerritory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create({"name": "Test Branch Manager"})

        cls.region = cls.env["res.region"].create(
            {
                "name": "Test Region",
                "description": "Test Region Description",
                "partner_id": cls.partner.id,
            }
        )

        cls.district = cls.env["res.district"].create(
            {
                "name": "Test District",
                "region_id": cls.region.id,
                "partner_id": cls.partner.id,
            }
        )

        cls.branch = cls.env["res.branch"].create(
            {
                "name": "Test Branch",
                "partner_id": cls.partner.id,
                "district_id": cls.district.id,
            }
        )

        cls.territory = cls.env["res.territory"].create(
            {
                "name": "Test Territory",
                "branch_id": cls.branch.id,
                "description": "Test Territory Description",
                "type": "state",
                "zip_codes": "12345, 67890",
            }
        )

    def test_create_territory(self):
        self.assertEqual(
            self.territory.name, "Test Territory", "Territory name mismatch"
        )
        self.assertEqual(
            self.territory.description,
            "Test Territory Description",
            "Territory description mismatch",
        )
        self.assertEqual(self.territory.branch_id, self.branch, "Branch mismatch")
        self.assertEqual(self.territory.district_id, self.district, "District mismatch")
        self.assertEqual(self.territory.region_id, self.region, "Region mismatch")
        self.assertEqual(self.territory.type, "state", "Territory type mismatch")
        self.assertEqual(self.territory.zip_codes, "12345, 67890", "ZIP codes mismatch")

    def test_update_territory(self):
        new_branch = self.env["res.branch"].create({"name": "New Test Branch"})
        self.territory.write({"branch_id": new_branch.id, "type": "zip"})
        self.assertEqual(
            self.territory.branch_id, new_branch, "Branch was not updated correctly"
        )
        self.assertEqual(
            self.territory.type, "zip", "Territory type was not updated correctly"
        )

    def test_add_country_to_territory(self):
        country = self.env["res.country"].create(
            {"name": "Test Country", "territory_id": self.territory.id, "code": "TS"}
        )
        self.assertIn(
            country, self.territory.country_ids, "Country was not added to territory"
        )

    def test_unlink_territory(self):
        territory_id = self.territory.id
        self.territory.unlink()
        self.assertFalse(
            self.env["res.territory"].search([("id", "=", territory_id)]),
            "Territory was not deleted",
        )
