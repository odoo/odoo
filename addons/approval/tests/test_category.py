from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestCategorySequenceCodeDerivation(common.TransactionCase):
    def test_derived_code_skips_a_code_held_by_an_archived_category(self):
        category = self.env["approval.category"].create(
            {"name": "Archived Holder", "sequence_code": "ARCHHOLD"},
        )
        category.active = False
        self.env.flush_all()

        fresh = self.env["approval.category"].create({"name": "ARCHHOLD"})

        self.assertNotEqual(
            fresh.sequence_code,
            "ARCHHOLD",
            "The derived code must step past the archived category's code.",
        )
        self.assertTrue(fresh.sequence_code.startswith("ARCHHOLD"))

    def test_derived_code_skips_a_code_held_by_an_active_category(self):
        self.env["approval.category"].create(
            {"name": "Active Holder", "sequence_code": "ACTVHOLD"},
        )
        self.env.flush_all()

        fresh = self.env["approval.category"].create({"name": "ACTVHOLD"})

        self.assertNotEqual(fresh.sequence_code, "ACTVHOLD")
