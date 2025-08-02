# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon


class TestMailPluginProjectController(TestMailPluginControllerCommon):
    def test_user_lang(self):
        """Verify that we translate field in the user language."""
        self.env["res.lang"]._activate_lang("fr_BE")
        self.env["res.lang"]._activate_lang("es_ES")
        project = self.env["project.project"].create({"name": "Test Mail Plugin"})
        project.with_context(lang="fr_BE").name = "[FR] Test Mail Plugin"
        self.assertEqual(project.name, "Test Mail Plugin")

        for lang, expected in (
            (False, "Test Mail Plugin"),
            ("en_US", "Test Mail Plugin"),
            ("fr_BE", "[FR] Test Mail Plugin"),
            ("es_ES", "Test Mail Plugin"),  # no translation
        ):
            self.user_test.lang = lang

            data = {
                "id": 0,
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"search_term": "Test Mail Plugin"},
            }

            with patch.object(
                type(self.env["res.users.apikeys"]),
                "_check_credentials",
                new=lambda *args, **kwargs: self.user_test.id,
            ):
                result = self.url_open(
                    "/mail_plugin/project/search",
                    data=json.dumps(data).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "dummy",
                    },
                )

            result = result.json().get("result")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["project_id"], project.id)
            self.assertEqual(result[0]["name"], expected)
