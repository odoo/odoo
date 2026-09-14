from psycopg.errors import UniqueViolation

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCategoryFieldDefinitions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env["credential.category"].create(
            {"name": "Portal Login", "code": "portal_login", "storage_hint": "json"}
        )

    def _definition(self, **vals):
        return self.env["credential.category.field"].create(
            {"category_id": self.category.id, **vals}
        )

    def _credential(self, **vals):
        return self.env["credential.credential"].create(
            {"name": "portal", "category_id": self.category.id, **vals}
        )

    def test_a_category_with_no_definitions_requires_nothing(self):
        self.assertTrue(self._credential(password="x"))

    def test_a_credential_without_a_secret_is_unprovisioned_not_invalid(self):
        self._definition(code="username", name="Username")
        credential = self._credential()
        self.assertFalse(credential.is_provisioned)
        with self.assertRaises(ValidationError) as caught:
            credential.password = "x"
        self.assertIn("username", str(caught.exception))

    def test_a_required_definition_is_enforced_without_any_python(self):
        self._definition(code="username", name="Username")
        with self.assertRaises(ValidationError) as caught:
            self._credential(password="x")
        self.assertIn("username", str(caught.exception))

    def test_the_requirement_names_the_payload_key_not_the_label(self):
        self._definition(code="oauth_client_secret", name="Client Secret")
        with self.assertRaises(ValidationError) as caught:
            self._credential(password="x")
        self.assertIn("oauth_client_secret", str(caught.exception))

    def test_a_definition_is_satisfied_from_the_encrypted_payload(self):
        self._definition(code="username", name="Username")
        credential = self._credential(username="luis")
        self.assertEqual(credential.username, "luis")

    def test_a_definition_that_is_not_required_is_not_demanded(self):
        self._definition(code="username", name="Username", required=False)
        self.assertTrue(self._credential())

    def test_members_of_a_requirement_group_satisfy_each_other(self):
        self._definition(
            code="oauth_access_token", name="Access Token", requirement_group="token"
        )
        self._definition(
            code="oauth_refresh_token",
            name="Refresh Token",
            requirement_group="token",
            sequence=20,
        )
        self.assertTrue(self._credential(oauth_refresh_token="r"))

    def test_a_requirement_group_is_unsatisfied_when_every_member_is_empty(self):
        self._definition(
            code="oauth_access_token", name="Access Token", requirement_group="token"
        )
        self._definition(
            code="oauth_refresh_token",
            name="Refresh Token",
            requirement_group="token",
            sequence=20,
        )
        with self.assertRaises(ValidationError):
            self._credential(password="x")

    def test_the_message_is_generated_when_the_category_states_none(self):
        self._definition(code="username", name="Username")
        self._definition(code="password", name="Password", sequence=20)
        self.assertEqual(
            self.category._requirement_message(),
            "Portal Login credentials require Username, Password.",
        )

    def test_a_group_reads_as_alternatives_in_the_generated_message(self):
        self._definition(
            code="oauth_access_token", name="Access Token", requirement_group="token"
        )
        self._definition(
            code="oauth_refresh_token",
            name="Refresh Token",
            requirement_group="token",
            sequence=20,
        )
        self.assertEqual(
            self.category._requirement_message(),
            "Portal Login credentials require Access Token or Refresh Token.",
        )

    def test_the_category_message_wins_over_the_generated_one(self):
        self.category.requirement_message = "This portal wants a login."
        self._definition(code="username", name="Username")
        self.assertEqual(
            self.category._requirement_message(), "This portal wants a login."
        )

    def test_a_code_that_cannot_be_a_payload_key_is_refused(self):
        with self.assertRaises(ValidationError):
            self._definition(code="User Name", name="Username")

    @mute_logger("odoo.sql_db")
    def test_a_category_names_each_of_its_fields_once(self):
        self._definition(code="username", name="Username")
        with self.assertRaises(UniqueViolation):
            with self.env.cr.savepoint():
                self._definition(code="username", name="Login")

    def test_the_simple_storage_value_is_not_offered_as_a_payload_key(self):
        definition = self._definition(code="credential_value", name="Secret")
        self.assertFalse(definition.is_blob_key)

    def test_every_other_code_is_a_payload_key(self):
        definition = self._definition(code="username", name="Username")
        self.assertTrue(definition.is_blob_key)

    def test_the_shipped_categories_carry_their_requirements_as_data(self):
        basic_auth = self.env.ref("credential.credential_category_basic_auth")
        self.assertEqual(basic_auth.field_ids.mapped("code"), ["username", "password"])
        self.assertTrue(all(basic_auth.field_ids.mapped("required")))
