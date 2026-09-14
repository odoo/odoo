from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestSecretValues(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_basic_auth")
        cls.credential = cls.env["credential.credential"].create(
            {
                "name": "portal login",
                "category_id": cls.category.id,
                "username": "luis",
                "password": "s3cr3t",
            }
        )

    def _entries(self, credential=None):
        entries = (credential or self.credential).secret_values
        return {entry["code"]: entry for entry in entries}

    def _write(self, **values):
        entries = [
            {
                **entry,
                **({"value": values[entry["code"]]} if entry["code"] in values else {}),
            }
            for entry in self.credential.secret_values
        ]
        self.credential.secret_values = entries

    def test_an_entry_carries_its_label_and_never_its_value(self):
        entry = self._entries()["password"]
        self.assertEqual(entry["label"], "Password")
        self.assertTrue(entry["required"])
        self.assertNotIn("value", entry)

    def test_the_client_is_told_which_fields_hold_a_value(self):
        entries = self._entries()
        self.assertTrue(entries["username"]["filled"])
        self.assertTrue(entries["password"]["filled"])

    def test_the_stored_value_is_nowhere_in_what_the_client_receives(self):
        self.assertNotIn("s3cr3t", str(self.credential.secret_values))

    def test_a_field_the_category_declares_but_nobody_filled_reads_unfilled(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "half filled",
                "category_id": self.env.ref("credential.credential_category_oauth2").id,
                "oauth_refresh_token": "r",
            }
        )
        entries = self._entries(credential)
        self.assertFalse(entries["oauth_client_id"]["filled"])
        self.assertTrue(entries["oauth_refresh_token"]["filled"])

    def test_the_entries_follow_the_declared_sequence(self):
        self.assertEqual(
            [entry["code"] for entry in self.credential.secret_values],
            ["username", "password"],
        )

    def test_the_simple_storage_value_is_not_offered_as_an_entry(self):
        credential = self.env["credential.credential"].create(
            {
                "name": "an api key",
                "category_id": self.env.ref(
                    "credential.credential_category_api_key"
                ).id,
                "credential_value": "k",
            }
        )
        self.assertNotIn("credential_value", self._entries(credential))

    def test_writing_a_value_stores_it(self):
        self._write(password="rotated")
        self.assertEqual(self.credential.password, "rotated")

    def test_writing_an_empty_value_clears_the_key(self):
        self._write(username="")
        self.assertFalse(self.credential.username)
        self.assertEqual(self.credential.password, "s3cr3t")

    def test_writing_the_entries_back_untouched_changes_nothing(self):
        self.credential.secret_values = self.credential.secret_values
        self.assertEqual(self.credential.username, "luis")
        self.assertEqual(self.credential.password, "s3cr3t")

    def test_one_retyped_field_leaves_its_neighbours_alone(self):
        self._write(password="rotated")
        self.assertEqual(self.credential.username, "luis")
        self.assertEqual(self.credential.password, "rotated")

    def test_a_key_the_category_does_not_declare_is_refused(self):
        with self.assertRaises(ValidationError):
            self.credential.secret_values = [{"code": "api_key", "value": "smuggled"}]

    def test_revealing_returns_the_stored_value(self):
        self.assertEqual(
            self.credential.action_reveal_secret_field("password"), "s3cr3t"
        )

    def test_revealing_writes_exactly_one_audit_entry(self):
        Log = self.env["credential.access.log"]
        domain = [
            ("credential_id", "=", self.credential.id),
            ("operation", "=", "read"),
        ]
        before = Log.sudo().search_count(domain)
        self.credential.action_reveal_secret_field("password")
        self.assertEqual(Log.sudo().search_count(domain), before + 1)

    def test_revealing_a_key_the_category_does_not_declare_is_refused(self):
        with self.assertRaises(ValidationError):
            self.credential.action_reveal_secret_field("api_key")

    def test_revealing_past_the_cap_is_refused(self):
        self.credential.sudo().write(
            {"decrypt_rate_limit_enabled": True, "decrypt_rate_limit_max": 1}
        )
        self.credential.action_reveal_secret_field("password")
        with self.assertRaises(UserError):
            for _ in range(5):
                self.credential.action_reveal_secret_field("password")
