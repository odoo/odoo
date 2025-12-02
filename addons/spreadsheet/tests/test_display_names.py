from odoo.tests.common import TransactionCase, new_test_user


class TestDisplayNames(TransactionCase):

    def test_get_single_display_name(self):
        bob = self.env["res.partner"].create({"name": "Bob"})
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([{"model": "res.partner", "id": bob.id}])
        self.assertEqual(display_name, ["Bob"])

    def test_get_archived_record_display_name(self):
        bob = self.env["res.partner"].create({"name": "Bob", "active": False})
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([{"model": "res.partner", "id": bob.id}])
        self.assertEqual(display_name, ["Bob"])

    def test_two_single_display_name(self):
        alice = self.env["res.partner"].create({"name": "Alice"})
        bob = self.env["res.partner"].create({"name": "Bob"})
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([
            {"model": "res.partner", "id": alice.id},
            {"model": "res.partner", "id": bob.id}
        ])
        self.assertEqual(display_name, ["Alice", "Bob"])

    def test_get_missing_id_display_name(self):
        self.assertFalse(self.env["res.partner"].browse(9999).exists())
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([
            {"model": "res.partner", "id": 9999}
        ])
        self.assertEqual(display_name, [None])

    def test_get_mix_missing_correct_ids_display_name(self):
        bob = self.env["res.partner"].create({"name": "Bob"})
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([
            {"model": "res.partner", "id": bob.id},
            {"model": "res.partner", "id": 9999},
        ])
        self.assertEqual(display_name, ["Bob", None])

    def test_mixed_model_display_name(self):
        alice = new_test_user(self.env, login="alice", name="Alice")
        bob = self.env["res.partner"].create({"name": "Bob"})
        display_name = self.env["spreadsheet.mixin"].get_display_names_for_spreadsheet([
            {"model": "res.users", "id": alice.id},
            {"model": "res.partner", "id": bob.id}
        ])
        self.assertEqual(display_name, ["Alice", "Bob"])
