from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGetSecret(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key_category = cls.env.ref("credential.credential_category_api_key")
        cls.bearer_category = cls.env.ref("credential.credential_category_bearer_token")

    def _create(self, name, category, **payload):
        return self.env["credential.credential"].create(
            {"name": name, "category_id": category.id, **payload}
        )

    def test_simple_storage(self):
        credential = self._create(
            "simple secret", self.api_key_category, credential_value="PLAIN"
        )
        self.assertEqual(credential.storage_method, "simple")
        self.assertFalse(credential.api_key, "sanity: the accessor is empty here")
        self.assertEqual(credential._get_secret(), "PLAIN")

    def test_json_storage(self):
        credential = self._create("json secret", self.api_key_category, api_key="KEYED")
        self.assertEqual(credential.storage_method, "json")
        self.assertFalse(
            credential.credential_value, "sanity: the simple field is empty here"
        )
        self.assertEqual(credential._get_secret(), "KEYED")

    def test_prefer_disambiguates_a_multi_secret_record(self):
        credential = self._create(
            "two secrets",
            self.bearer_category,
            bearer_token="BEARER",
            api_secret="SECRET",
        )
        self.assertEqual(credential._get_secret(prefer="bearer_token"), "BEARER")
        self.assertEqual(credential._get_secret(prefer="api_secret"), "SECRET")

    def test_prefer_falls_through_when_that_slot_is_empty(self):
        credential = self._create("one secret", self.api_key_category, api_key="ONLY")
        self.assertEqual(
            credential._get_secret(prefer="bearer_token"),
            "ONLY",
            "a preference is a hint, not a filter",
        )

    def test_empty_credential(self):
        credential = self._create(
            "no payload yet",
            self.env.ref("credential.credential_category_custom"),
        )
        self.assertFalse(credential._get_secret())

    def test_form_save_keeps_the_key_beside_empty_siblings(self):
        # The form sends every accessor and the JSON blob on one save: the key,
        # eight empty siblings and ``credential_data == "{}"``. None of the
        # empties may erase the key written in the same create().
        empties = {
            name: False
            for name in self.env["credential.credential"]._JSON_ACCESSOR_FIELDS
            if name != "api_key"
        }
        credential = self._create(
            "form save",
            self.api_key_category,
            api_key="KEYED",
            credential_data="{}",
            credential_value=False,
            **empties,
        )
        credential.invalidate_recordset()
        self.assertTrue(credential.credential_value_encrypted)
        self.assertEqual(credential._get_secret(prefer="api_key"), "KEYED")
