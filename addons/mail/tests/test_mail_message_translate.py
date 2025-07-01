# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests
from http import HTTPStatus
from unittest.mock import patch

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests.common import JsonRpcException, new_test_user, tagged
from odoo.tools import mute_logger

SAMPLE = {
    "text": "<p>Al mal tiempo, buena cara.</p>",
    "src": "es",
    "en": "<p>To bad weather, good face.</p>",
    "fr": "<p>Au mauvais temps, bonne tête.</p>",
    "nl": "<script src='xss-min.js'/><p onclick='XSS()'>Bij slecht weer, goed gezicht.</p>",
    "lang": {
        "fr": "espagnol",
        "en": "Spanish",
    },
}


def mock_response(fun):
    def wrapper(self, url, data=False, params=False, timeout=5):
        response = requests.Response()
        response.status_code = HTTPStatus.OK
        content = {"data": fun(self, url=url, data=data, params=params)}
        if not content["data"]:
            response.status_code = HTTPStatus.BAD_REQUEST
            content = {"error": {"message": "Mocked Error"}}
        response._content = json.dumps(content).encode()
        return response

    return wrapper


# Google Cloud Translation Documentation: https://cloud.google.com/translate/docs/reference/api-overview?hl=en
@tagged("post_install", "-at_install", "mail_message")
class TestTranslationController(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["res.lang"]._activate_lang("en_US")
        cls.env.ref("base.user_admin").write({"lang": "fr_FR"})
        cls.api_key = "VALIDKEY"
        cls.env["ir.config_parameter"].set_param("mail.google_translate_api_key", cls.api_key)
        cls.message = cls.env["mail.message"].create(
            {
                "body": SAMPLE["text"],
                "model": "res.partner",
                "res_id": cls.env.ref("base.user_admin").partner_id.id,
                "message_type": "comment",
            }
        )
        cls.request_count = 0

    @mock_response
    def _patched_post(self, url, data, params, timeout=5):
        self.request_count += 1
        if f"/v2/detect?key={self.api_key}" in url:
            result = {
                "language": SAMPLE["src"],
                "isReliable": True,
                "confidence": 0.98,
            }
            return {"detections": [[result]]}
        if f"/v2/?key={self.api_key}" in url:
            return {"translations": [{"translatedText": SAMPLE[data.get("target")]}]}

    def _mock_translation_request(self, data):
        with patch.object(requests, "post", self._patched_post):
            return self.make_jsonrpc_request("/mail/message/translate", data)

    def test_update_message(self):
        self.authenticate("admin", "admin")
        result = self._mock_translation_request({"message_id": self.message.id})
        self.assertFalse(result.get("error"))
        self.assertEqual(self.env["mail.message.translation"].search_count([]), 1)
        # The translation records should not be discarded if the body did not change.
        self.make_jsonrpc_request(
            "/mail/message/update_content", {"message_id": self.message.id, "body": None, "attachment_ids": []}
        )
        self.assertEqual(self.env["mail.message.translation"].search_count([]), 1)
        self.make_jsonrpc_request(
            "/mail/message/update_content", {"message_id": self.message.id, "body": "update", "attachment_ids": []}
        )
        self.assertFalse(self.env["mail.message.translation"].search_count([]))

    def test_translation_multi_users(self):
        new_test_user(self.env, "user_test_fr", groups="base.group_user", lang="fr_FR")
        new_test_user(self.env, "user_test_en", groups="base.group_user", lang="en_US")
        for login, target_lang in [("user_test_fr", "fr"), ("user_test_en", "en"), ("admin", "fr")]:
            self.authenticate(login, login)
            result = self._mock_translation_request({"message_id": self.message.id})
            self.assertFalse(result.get("error"))
            self.assertEqual(result["body"], SAMPLE[target_lang])
            self.assertEqual(result["lang_name"], SAMPLE["lang"][target_lang])
        # There is one translation record per target language.
        self.assertEqual(self.env["mail.message.translation"].search_count([]), 2)
        # No API request should be sent if a translation value or source already exists.
        self.assertEqual(self.request_count, 3)

    def test_invalid_api_key(self):
        self.env["ir.config_parameter"].set_param("mail.google_translate_api_key", "INVALIDKEY")
        self.authenticate("demo", "demo")
        result = self._mock_translation_request({"message_id": self.message.id})
        self.assertNotIn("body", result)
        self.assertNotIn("lang_name", result)
        self.assertTrue(result["error"])

    def test_html_sanitization(self):
        self.env["res.lang"]._activate_lang("nl_NL")
        new_test_user(self.env, "user_test_nl", groups="base.group_user", lang="nl_NL")
        self.authenticate("user_test_nl", "user_test_nl")
        result = self._mock_translation_request({"message_id": self.message.id})
        self.assertFalse(result.get("error"))
        self.assertHTMLEqual(result["body"], "<p>Bij slecht weer, goed gezicht.</p>")
        translation = self.env["mail.message.translation"].search([])
        self.assertEqual(len(translation), 1)
        self.assertHTMLEqual(translation.body, "<p>Bij slecht weer, goed gezicht.</p>")

    def test_access_right(self):
        with self.assertRaises(JsonRpcException, msg="odoo.http.SessionExpiredException"):
            self._mock_translation_request({"message_id": self.message.id})
        new_test_user(self.env, "user_test_portal", groups="base.group_portal", lang="fr_FR")
        self.authenticate("user_test_portal", "user_test_portal")
        with self.assertRaises(JsonRpcException, msg="odoo.exceptions.AccessError"), mute_logger("odoo.http"):
            self._mock_translation_request({"message_id": self.message.id})

    def test_unknown_language(self):
        self.authenticate("admin", "admin")
        with patch.dict(SAMPLE, {"src": "unknown_by_babel_but_known_by_google_api"}):
            result = self._mock_translation_request({"message_id": self.message.id})
        self.assertEqual(result["body"], "<p>Au mauvais temps, bonne tête.</p>")
