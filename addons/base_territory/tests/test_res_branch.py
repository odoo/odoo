from odoo.tests.common import TransactionCase


class TestResBranch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "email": "test_partner@example.com"}
        )

        cls.district = cls.env["res.district"].create({"name": "Test District"})

    def create_branch(self, **kwargs):
        return self.env["res.branch"].create(
            {
                "name": "Test Branch",
                "partner_id": self.partner.id,
                "district_id": self.district.id,
                **kwargs,
            }
        )

    def test_create_branch(self):
        branch = self.create_branch(description="Main Branch")
        self.assertEqual(branch.name, "Test Branch", "Branch name mismatch")
        self.assertEqual(branch.partner_id, self.partner, "Branch partner mismatch")
        self.assertEqual(branch.district_id, self.district, "Branch district mismatch")
        self.assertEqual(
            branch.description, "Main Branch", "Branch description mismatch"
        )

    def test_update_branch(self):
        branch = self.create_branch()
        branch.write({"name": "Updated Branch"})
        self.assertEqual(branch.name, "Updated Branch", "Branch name was not updated")

    def test_unlink_branch(self):
        branch = self.create_branch()
        branch_id = branch.id
        branch.unlink()
        self.assertFalse(
            self.env["res.branch"].search([("id", "=", branch_id)]),
            "Branch was not deleted",
        )
