from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.service.api_scope import SAFE_CONTEXT_KEYS
from odoo.tests import common, get_db_name, tagged
from odoo.tools import authority_keys as authority_keys_module
from odoo.tools import mute_logger
from odoo.tools.authority_keys import (
    authority_keys,
    declare_authority_keys,
    is_authority_key,
    strip_authority_keys,
)

from odoo.addons.base.tests.common import HttpCaseWithUserDemo

FORGED = {
    "skip_readonly_check": True,
    "install_mode": True,
    "uid": 1,
    "force_company": 1,
    "approval_binding_admitted": [["account.move", "action_post", [1]]],
}
PREFERENCES = {
    "lang": "en_US",
    "tz": "UTC",
    "active_test": False,
    "default_name": "kept",
    "test_rpc_ui_key": 1,
}


class TestAuthorityKeyRegistry(common.BaseCase):
    def test_seed_declares_the_classified_keys(self):
        for key in FORGED:
            self.assertTrue(is_authority_key(key), key)
        for key in PREFERENCES:
            self.assertFalse(is_authority_key(key), key)

    def test_no_api_scope_safe_key_is_an_authority_key(self):
        self.assertFalse(SAFE_CONTEXT_KEYS & set(authority_keys()))

    def test_an_addon_extends_the_registry_at_import(self):
        key = "test_rpc_declared_at_import"
        self.enterContext(patch.dict(authority_keys_module._AUTHORITY_KEYS))
        self.assertEqual(strip_authority_keys({key: 1}), {key: 1})
        declare_authority_keys("test_rpc", key)
        self.assertEqual(
            strip_authority_keys({key: 1, "lang": "fr_FR"}), {"lang": "fr_FR"}
        )

    def test_strip_returns_the_same_mapping_when_nothing_is_dropped(self):
        context = {"lang": "en_US"}
        self.assertIs(strip_authority_keys(context), context)
        self.assertIsNone(strip_authority_keys(None))


@tagged("-at_install", "post_install")
class TestAuthorityKeyDoors(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo.group_ids = cls.env.ref("base.group_user")

    def setUp(self):
        super().setUp()
        self.authenticate("demo", "demo")

    def assertDoorStrips(self, keys):
        self.assertFalse(set(FORGED) & set(keys), keys)
        self.assertLessEqual(set(PREFERENCES), set(keys))

    def _call(self, route, method="echo_context_keys"):
        return self.call_jsonrpc(
            route,
            {
                "model": "test_rpc.model_a",
                "method": method,
                "args": [],
                "kwargs": {"context": {**FORGED, **PREFERENCES}},
            },
        )

    def test_call_kw_strips_authority_keys(self):
        self.assertDoorStrips(self._call("/web/dataset/call_kw"))

    def test_call_button_strips_authority_keys(self):
        action = self._call("/web/dataset/call_button", "echo_context_action")
        self.assertDoorStrips(action["params"]["keys"])

    def test_jsonrpc_route_context_param_strips_authority_keys(self):
        keys = self.call_jsonrpc(
            "/test_rpc/echo_context_keys", {"context": {**FORGED, **PREFERENCES}}
        )
        self.assertDoorStrips(keys)

    def test_xmlrpc_strips_authority_keys(self):
        with mute_logger("odoo.addons.rpc.controllers.xmlrpc"):
            keys = self.xmlrpc_object.execute_kw(
                get_db_name(),
                self.user_demo.id,
                "demo",
                "test_rpc.model_a",
                "echo_context_keys",
                [],
                {"context": {**FORGED, **PREFERENCES}},
            )
        self.assertDoorStrips(keys)

    def test_json2_strips_authority_keys(self):
        api_key = (
            self.env["res.users.apikeys"]
            .with_user(self.user_demo)
            ._generate(None, "authority keys", datetime.now() + timedelta(days=1))
        )
        with mute_logger("odoo.http"):
            response = self.url_open(
                "/json/2/test_rpc.model_a/echo_context_keys",
                json={"context": {**FORGED, **PREFERENCES}},
                headers={"Authorization": f"Bearer {api_key}"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertDoorStrips(response.json())

    def test_a_server_side_caller_keeps_its_authority_keys(self):
        keys = (
            self.env["test_rpc.model_a"]
            .with_user(self.user_demo)
            .with_context(skip_readonly_check=True, install_mode=True)
            .echo_context_keys()
        )
        self.assertIn("skip_readonly_check", keys)
        self.assertIn("install_mode", keys)

    def test_forged_uid_does_not_change_the_caller(self):
        uid = self.call_jsonrpc(
            "/web/dataset/call_kw",
            {
                "model": "res.users",
                "method": "search",
                "args": [[["id", "=", self.user_demo.id]]],
                "kwargs": {"context": {"uid": 1}},
            },
        )
        self.assertEqual(uid, [self.user_demo.id])
