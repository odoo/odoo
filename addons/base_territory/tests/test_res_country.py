from odoo.tests.common import TransactionCase


class TestResCountry(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.territory = cls.env["res.territory"].create({"name": "Test Territory"})
        cls.region1 = cls.env["res.region"].create({"name": "Test Region 1"})
        cls.region2 = cls.env["res.region"].create({"name": "Test Region 2"})

        cls.country = cls.env["res.country"].create(
            {
                "name": "Test Country",
                "code": "TE",
                "territory_id": cls.territory.id,
                "region_ids": [(6, 0, [cls.region1.id, cls.region2.id])],
            }
        )

    def test_create_country(self):
        self.assertEqual(self.country.name, "Test Country", "Country name mismatch")
        self.assertEqual(self.country.code, "TE", "Country code mismatch")
        self.assertEqual(
            self.country.territory_id, self.territory, "Country territory mismatch"
        )
        self.assertIn(
            self.region1, self.country.region_ids, "Region 1 not correctly linked"
        )
        self.assertIn(
            self.region2, self.country.region_ids, "Region 2 not correctly linked"
        )

    def test_update_country_territory(self):
        new_territory = self.env["res.territory"].create({"name": "New Territory"})
        self.country.write({"territory_id": new_territory.id})
        self.assertEqual(
            self.country.territory_id, new_territory, "Territory was not updated"
        )

    def test_update_country_regions(self):
        new_region = self.env["res.region"].create({"name": "Test Region 3"})
        self.country.write({"region_ids": [(6, 0, [new_region.id])]})
        self.assertEqual(
            len(self.country.region_ids), 1, "Region count after update is incorrect"
        )
        self.assertIn(
            new_region, self.country.region_ids, "New region was not added correctly"
        )

    def test_unlink_country(self):
        country_id = self.country.id
        self.country.unlink()
        self.assertFalse(
            self.env["res.country"].search([("id", "=", country_id)]),
            "Country was not deleted",
        )
