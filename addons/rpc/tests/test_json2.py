from odoo.tests import common
from odoo.tools import mute_logger


@common.tagged("post_install", "-at_install")
class TestJson2(common.HttpCase):
    def setUp(self):
        super().setUp()
        admin = self.env.ref("base.user_admin")
        self.api_key = (
            self.env["res.users.apikeys"]
            .with_user(admin)
            ._generate("rpc", "json2 test key", None)
        )
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        self.enterContext(mute_logger("odoo.http"))

    def _rpc(self, model, method, payload):
        return self.url_open(
            f"/json/2/{model}/{method}", json=payload, headers=self.headers
        )

    def test_json2_root_hints_correct_usage(self):
        response = self.url_open("/json/2")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Did you mean", response.text)

    def test_json2_rpc_returns_result(self):
        response = self._rpc("res.partner", "search_count", {"domain": []})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json(), 1)

    def test_json2_read_group_serializes(self):
        response = self._rpc(
            "res.partner",
            "formatted_read_group",
            {"domain": [], "groupby": ["parent_id"], "aggregates": ["color:sum"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsInstance(response.json(), list)

    def test_json2_name_search_serializes(self):
        response = self._rpc("res.partner", "name_search", {"name": "admin"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json())

    def test_json2_unknown_model_is_404(self):
        response = self._rpc("does.not.exist", "read", {})
        self.assertEqual(response.status_code, 404)

    def test_json2_model_method_with_ids_is_422(self):
        response = self._rpc(
            "res.partner", "create", {"ids": [1], "vals_list": [{"name": "X"}]}
        )
        self.assertEqual(response.status_code, 422)

    def test_json2_bad_signature_is_422(self):
        response = self._rpc("res.partner", "search_count", {"bogus_kwarg": 1})
        self.assertEqual(response.status_code, 422)
