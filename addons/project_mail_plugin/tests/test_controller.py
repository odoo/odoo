import json

from odoo.addons.mail_plugin.tests.common import (
    TestMailPluginControllerCommon,
    as_outlook_user,
)


class TestMailPluginProjectController(TestMailPluginControllerCommon):
    @as_outlook_user("employee")
    def test_user_lang(self):
        self.env["res.lang"]._activate_lang("fr_BE")
        self.env["res.lang"]._activate_lang("es_ES")
        project = self.env["project.project"].create({"name": "Test Mail Plugin"})
        project.with_context(lang="fr_BE").name = "[FR] Test Mail Plugin"
        self.assertEqual(project.name, "Test Mail Plugin")

        for lang, expected in (
            (False, "Test Mail Plugin"),
            ("en_US", "Test Mail Plugin"),
            ("fr_BE", "[FR] Test Mail Plugin"),
            ("es_ES", "Test Mail Plugin"),
        ):
            self.user_test.lang = lang

            data = {
                "id": 0,
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"search_term": "Test Mail Plugin"},
            }

            result = self.url_open(
                "/mail_plugin/project/search",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )

            result = result.json().get("result")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["project_id"], project.id)
            self.assertEqual(result[0]["name"], expected)
