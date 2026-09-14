from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools import get_api_client


class _FakeResponse:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, payload):
        self._payload = payload
        self.text = f'{{"secret": "{payload}"}}'
        self.content = self.text.encode()

    def json(self):
        return {"secret": self._payload}

    def raise_for_status(self):
        pass


@tagged("post_install", "-at_install")
class TestCacheIsScopedByCredential(TransactionCase):
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
            {"name": "Alice", "login": "alice_cache_scope", "group_ids": groups}
        )
        cls.bob = cls.env["res.users"].create(
            {"name": "Bob", "login": "bob_cache_scope", "group_ids": groups}
        )

    def _endpoint(self, code, allow_user=True):
        return self.env["integration.service"].create(
            {
                "name": code,
                "code": code,
                "endpoint_url": "https://example.invalid/api",
                "auth_type": "bearer",
                "allow_user_credentials": allow_user,
                "cache_enabled": True,
                "cache_ttl": 3600,
            }
        )

    def _credential(self, endpoint, name, owner=None):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "endpoint_id": endpoint.id,
                "category_id": self.category.id,
                "bearer_token": f"T-{name}",
                "owner_user_id": owner.id if owner else False,
                "company_id": self.env.company.id,
            }
        )

    def test_a_personal_credential_does_not_read_another_users_cache(self):
        endpoint = self._endpoint("cache_scope_personal")
        self._credential(endpoint, "alice", owner=self.alice)
        self._credential(endpoint, "bob", owner=self.bob)
        self.env.flush_all()

        alice_client = get_api_client(self.env(user=self.alice.id), endpoint.code)
        bob_client = get_api_client(self.env(user=self.bob.id), endpoint.code)
        self.assertNotEqual(
            alice_client.credential,
            bob_client.credential,
            "the endpoint must resolve a different credential per user, "
            "otherwise this test proves nothing",
        )

        served = []

        def fake_request(_session, method=None, url=None, **kwargs):
            served.append(url)
            return _FakeResponse("ALICE-ONLY" if len(served) == 1 else "BOB-ONLY")

        with patch("requests.Session.request", fake_request):
            alice_body = alice_client.get("/me")
            self.env.flush_all()
            bob_body = bob_client.get("/me")

        self.assertEqual(
            len(served),
            2,
            "Bob's call must reach the network instead of being served from "
            "the cache entry Alice populated",
        )
        self.assertEqual(alice_body["body"]["secret"], "ALICE-ONLY")
        self.assertEqual(bob_body["body"]["secret"], "BOB-ONLY")

    def test_one_shared_credential_still_shares_the_cache(self):
        endpoint = self._endpoint("cache_scope_shared", allow_user=False)
        self._credential(endpoint, "company")
        self.env.flush_all()

        first = get_api_client(self.env(user=self.alice.id), endpoint.code)
        second = get_api_client(self.env(user=self.bob.id), endpoint.code)
        self.assertEqual(
            first.credential,
            second.credential,
            "without personal credentials both users share the company one",
        )

        served = []

        def fake_request(_session, method=None, url=None, **kwargs):
            served.append(url)
            return _FakeResponse("SHARED")

        with patch("requests.Session.request", fake_request):
            first.get("/status")
            self.env.flush_all()
            cached = second.get("/status")

        self.assertEqual(len(served), 1, "a shared credential must still hit the cache")
        self.assertTrue(cached.get("from_cache"))
