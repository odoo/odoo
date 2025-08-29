from odoo.tests.common import TransactionCase


class TestResDistrict(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.region = cls.env["res.region"].create({"name": "Test Region"})
        cls.partner = cls.env["res.partner"].create({"name": "Test District Manager"})

        cls.district = cls.env["res.district"].create(
            {
                "name": "Test District",
                "region_id": cls.region.id,
                "partner_id": cls.partner.id,
                "description": "Test District Description",
            }
        )

    def test_create_district(self):
        self.assertEqual(self.district.name, "Test District", "District name mismatch")
        self.assertEqual(
            self.district.region_id, self.region, "District region mismatch"
        )
        self.assertEqual(
            self.district.partner_id, self.partner, "District manager mismatch"
        )
        self.assertEqual(
            self.district.description,
            "Test District Description",
            "District description mismatch",
        )

    def test_update_district_region(self):
        new_region = self.env["res.region"].create({"name": "New Region"})
        self.district.write({"region_id": new_region.id})
        self.assertEqual(
            self.district.region_id, new_region, "Region was not updated correctly"
        )

    def test_update_district_manager(self):
        new_partner = self.env["res.partner"].create({"name": "New District Manager"})
        self.district.write({"partner_id": new_partner.id})
        self.assertEqual(
            self.district.partner_id,
            new_partner,
            "District manager was not updated correctly",
        )

    def test_unlink_district(self):
        district_id = self.district.id
        self.district.unlink()
        self.assertFalse(
            self.env["res.district"].search([("id", "=", district_id)]),
            "District was not deleted",
        )
