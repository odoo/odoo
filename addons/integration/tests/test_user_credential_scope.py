from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools import get_api_client


@tagged("post_install", "-at_install")
class TestUserCredentialScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref("credential.credential_category_custom")
        groups = [
            (
                6,
                0,
                [
                    cls.env.ref("base.group_user").id,
                    cls.env.ref("credential.group_credential_user").id,
                ],
            )
        ]
        cls.alice = cls.env["res.users"].create(
            {"name": "Alice", "login": "alice_cred_scope", "group_ids": groups}
        )
        cls.bob = cls.env["res.users"].create(
            {"name": "Bob", "login": "bob_cred_scope", "group_ids": groups}
        )

    def _endpoint(self, code, allow_user=False):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/api",
                "auth_type": "bearer",
                "allow_user_credentials": allow_user,
            }
        )

    def _credential(self, endpoint, name, owner=None, company=None, sequence=10):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "endpoint_id": endpoint.id,
                "category_id": self.category.id,
                "bearer_token": f"T-{name}",
                "owner_user_id": owner.id if owner else False,
                "company_id": (company.id if company else self.env.company.id),
                "sequence": sequence,
            }
        )

    def _resolve(self, endpoint, user=None):
        return self.env["credential.credential"]._get_for_endpoint(endpoint, user=user)

    def test_a_personal_credential_wins_for_its_owner(self):
        endpoint = self._endpoint("scope_owner", allow_user=True)
        company_cred = self._credential(endpoint, "company")
        alice_cred = self._credential(endpoint, "alice", owner=self.alice)

        self.assertEqual(self._resolve(endpoint, self.alice), alice_cred)
        self.assertEqual(
            self._resolve(endpoint, self.bob),
            company_cred,
            "Bob has no personal credential, so the company one serves",
        )

    def test_a_user_without_one_falls_back_rather_than_failing(self):
        endpoint = self._endpoint("scope_fallback", allow_user=True)
        company_cred = self._credential(endpoint, "company")

        self.assertEqual(self._resolve(endpoint, self.alice), company_cred)

    def test_a_company_less_personal_credential_serves_every_company(self):
        endpoint = self._endpoint("scope_global_personal", allow_user=True)
        other_company = self.env["res.company"].create({"name": "Elsewhere"})
        personal = self.env["credential.credential"].create(
            {
                "name": "alice everywhere",
                "endpoint_id": endpoint.id,
                "category_id": self.category.id,
                "bearer_token": "T-anywhere",
                "owner_user_id": self.alice.id,
                "company_id": False,
            }
        )

        resolved = self.env["credential.credential"]._get_for_endpoint(
            endpoint, company=other_company, user=self.alice
        )
        self.assertEqual(resolved, personal)

    def test_an_endpoint_that_did_not_opt_in_is_unaffected(self):
        endpoint = self._endpoint("scope_opted_out", allow_user=False)
        company_cred = self._credential(endpoint, "company")
        self._credential(endpoint, "alice", owner=self.alice, sequence=1)

        self.assertEqual(
            self._resolve(endpoint, self.alice),
            company_cred,
            "a personal credential must be invisible to an endpoint that did "
            "not ask for personal credentials, even sorted first",
        )

    def test_another_users_credential_is_never_served_as_the_companys(self):
        endpoint = self._endpoint("scope_no_company_cred", allow_user=True)
        alice_cred = self._credential(endpoint, "alice", owner=self.alice, sequence=1)

        resolved = self._resolve(endpoint, self.bob)
        self.assertFalse(
            resolved,
            f"Bob resolved to {resolved.name!r}, which belongs to Alice",
        )
        self.assertEqual(self._resolve(endpoint, self.alice), alice_cred)

    def test_a_personal_credential_does_not_outrank_the_company_by_sequence(self):
        endpoint = self._endpoint("scope_sequence", allow_user=True)
        company_cred = self._credential(endpoint, "company", sequence=99)
        self._credential(endpoint, "alice", owner=self.alice, sequence=1)

        self.assertEqual(self._resolve(endpoint, self.bob), company_cred)

    def test_a_user_cannot_read_another_users_personal_credential(self):
        endpoint = self._endpoint("scope_privacy", allow_user=True)
        alice_cred = self._credential(endpoint, "alice", owner=self.alice)

        visible = (
            self.env["credential.credential"]
            .with_user(self.bob)
            .search([("id", "=", alice_cred.id)])
        )
        self.assertFalse(visible, "the record rule must hide it from Bob")
        self.assertTrue(
            self.env["credential.credential"]
            .with_user(self.alice)
            .search([("id", "=", alice_cred.id)]),
            "and must not hide it from Alice",
        )

    def test_a_company_credential_stays_visible_to_everyone(self):
        endpoint = self._endpoint("scope_privacy_company", allow_user=True)
        company_cred = self._credential(endpoint, "company")

        self.assertTrue(
            self.env["credential.credential"]
            .with_user(self.bob)
            .search([("id", "=", company_cred.id)])
        )

    def test_the_client_resolves_the_acting_users_credential(self):
        endpoint = self._endpoint("scope_client", allow_user=True)
        self._credential(endpoint, "company")
        alice_cred = self._credential(endpoint, "alice", owner=self.alice)

        client = get_api_client(self.env(user=self.alice), "scope_client")

        self.assertEqual(client.credential, alice_cred)

    def test_the_client_falls_back_for_a_user_without_one(self):
        endpoint = self._endpoint("scope_client_fallback", allow_user=True)
        company_cred = self._credential(endpoint, "company")

        client = get_api_client(self.env(user=self.bob), "scope_client_fallback")

        self.assertEqual(client.credential, company_cred)
