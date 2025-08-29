from odoo.tests.common import TransactionCase


class TestResRegion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create({"name": "Test Region Manager"})

        cls.region = cls.env["res.region"].create(
            {
                "name": "Test Region",
                "description": "Test Region Description",
                "partner_id": cls.partner.id,
            }
        )

    def test_create_region(self):
        self.assertEqual(self.region.name, "Test Region", "Region name mismatch")
        self.assertEqual(
            self.region.description,
            "Test Region Description",
            "Region description mismatch",
        )
        self.assertEqual(
            self.region.partner_id, self.partner, "Region manager mismatch"
        )

    def test_update_region_name(self):
        new_name = "Updated Region Name"
        self.region.write({"name": new_name})
        self.assertEqual(
            self.region.name, new_name, "Region name was not updated correctly"
        )

    def test_update_region_manager(self):
        new_partner = self.env["res.partner"].create({"name": "New Region Manager"})
        self.region.write({"partner_id": new_partner.id})
        self.assertEqual(
            self.region.partner_id,
            new_partner,
            "Region manager was not updated correctly",
        )

    def test_unlink_region(self):
        region_id = self.region.id
        self.region.unlink()
        self.assertFalse(
            self.env["res.region"].search([("id", "=", region_id)]),
            "Region was not deleted",
        )
