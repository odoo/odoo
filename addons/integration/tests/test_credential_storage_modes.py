from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCredentialStorageModes(TransactionCase):
    def _endpoint(self, code, auth_type):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/api",
                "auth_type": auth_type,
            }
        )

    def _credential(self, name, endpoint, **payload):
        credential = self.env["credential.credential"].create(
            {"name": name, "endpoint_id": endpoint.id, **payload}
        )
        endpoint.credential_id = credential
        endpoint.invalidate_recordset()
        return credential

    def test_bearer_endpoint_simple_storage_sends_authorization(self):
        endpoint = self._endpoint("bearer_simple", "bearer")
        credential = self._credential("bearer simple", endpoint, credential_value="TOK")
        self.assertEqual(credential.storage_method, "simple")
        self.assertEqual(
            credential._get_auth_headers(),
            {"Authorization": "Bearer TOK"},
            "a simple-storage bearer credential used to yield {} here, and the "
            "request went out with no Authorization header at all",
        )

    def test_bearer_endpoint_json_storage_sends_authorization(self):
        endpoint = self._endpoint("bearer_json", "bearer")
        credential = self._credential("bearer json", endpoint, bearer_token="TOK")
        self.assertEqual(credential.storage_method, "json")
        self.assertEqual(
            credential._get_auth_headers(), {"Authorization": "Bearer TOK"}
        )

    def test_api_key_endpoint_simple_storage_sends_the_key(self):
        endpoint = self._endpoint("key_simple", "api_key")
        credential = self._credential("key simple", endpoint, credential_value="K")
        self.assertEqual(
            credential._get_auth_headers(),
            endpoint._api_key_headers("K"),
            "the header SHAPE stays the endpoint's business; only where the key "
            "is read from changed",
        )

    def test_a_credential_with_no_payload_still_sends_nothing(self):
        endpoint = self._endpoint("empty", "bearer")
        credential = self.env["credential.credential"].create(
            {
                "name": "empty bearer",
                "endpoint_id": endpoint.id,
                "category_id": self.env.ref("credential.credential_category_custom").id,
            }
        )
        self.assertEqual(credential._get_auth_headers(), {})

    def test_fingerprint_and_token_check_for_json_storage(self):
        endpoint = self._endpoint("fp_json", "api_key")
        self._credential("fp json", endpoint, api_key="PRESENTED")

        self.assertTrue(
            endpoint.sudo().credential_fingerprint,
            "a json-storage credential used to fingerprint to False, so "
            "is_valid_token rejected the correct token on every request",
        )
        self.assertTrue(endpoint.is_valid_token("PRESENTED"))
        self.assertFalse(endpoint.is_valid_token("wrong"))

    def test_fingerprint_and_token_check_for_simple_storage(self):
        endpoint = self._endpoint("fp_simple", "bearer")
        self._credential("fp simple", endpoint, credential_value="PRESENTED")

        self.assertTrue(endpoint.sudo().credential_fingerprint)
        self.assertTrue(endpoint.is_valid_token("PRESENTED"))
        self.assertFalse(endpoint.is_valid_token("wrong"))

    def test_the_two_directions_agree_on_one_credential(self):
        for mode, payload in (
            ("simple", {"credential_value": "SHARED"}),
            ("json", {"bearer_token": "SHARED"}),
        ):
            with self.subTest(storage_method=mode):
                endpoint = self._endpoint(f"both_{mode}", "bearer")
                credential = self._credential(f"both {mode}", endpoint, **payload)
                self.assertEqual(credential.storage_method, mode)
                self.assertEqual(
                    credential._get_auth_headers(), {"Authorization": "Bearer SHARED"}
                )
                self.assertTrue(endpoint.is_valid_token("SHARED"))


@tagged("post_install", "-at_install")
class TestEndpointUnlinkAuditsItsCredentials(TransactionCase):
    def test_deleting_an_endpoint_audits_the_credentials_it_takes_with_it(self):
        endpoint = self.env["integration.service"].create(
            {
                "name": "cascade",
                "code": "cascade_probe",
                "endpoint_url": "https://example.invalid/api",
                "auth_type": "api_key",
            }
        )
        credential = self.env["credential.credential"].create(
            {"name": "cascade victim", "endpoint_id": endpoint.id, "api_key": "K"}
        )
        endpoint.credential_id = credential
        credential_id = credential.id

        endpoint.unlink()

        self.assertFalse(
            self.env["credential.credential"].browse(credential_id).exists()
        )
        rows = (
            self.env["credential.access.log"]
            .sudo()
            .search(
                [
                    ("operation", "=", "delete"),
                    ("credential_name", "=", "cascade victim"),
                ]
            )
        )
        self.assertEqual(
            len(rows),
            1,
            "the FK cascade used to remove the credential in SQL, skipping "
            "credential.credential.unlink() and writing no audit row at all",
        )
