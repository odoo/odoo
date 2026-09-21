from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import connect, disconnect
from odoo.addons.gateway_ml.tools.assistant_adoption import (
    adopt_assistant_columns,
    chat_model_for_code,
    connect_credential,
)


@tagged("post_install", "-at_install")
class TestAssistantAdoption(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.groq = cls.env.ref("gateway_ml.ai_provider_groq")
        cls.google = cls.env.ref("gateway_ml.ai_provider_google")
        cls.category = cls.env.ref("credential.credential_category_api_key")
        disconnect(cls.env, cls.groq)
        disconnect(cls.env, cls.google)

    def _loose_key(self, name="Bot AI key"):
        return self.env["credential.credential"].create(
            {
                "name": name,
                "category_id": self.category.id,
                "company_id": self.env.company.id,
                "api_key": "sk-bot",
            }
        )

    def _connected_credentials(self, provider):
        return {
            service.code: self.env["integration.connection"]
            ._resolve(service)
            .credential_id
            for service in provider.service_ids.service_id
        }

    def test_an_unknown_model_code_becomes_a_row_with_the_defaults_vision(self):
        row = chat_model_for_code(self.google, "gemini-next")
        self.assertEqual(row.provider_id, self.google)
        self.assertEqual(row.kind, "chat")
        self.assertTrue(row.has_vision)
        self.assertEqual(chat_model_for_code(self.google, "gemini-next"), row)
        self.assertFalse(chat_model_for_code(self.google, " "))

    def test_a_loose_key_connects_every_service_the_vendor_rides(self):
        credential = self._loose_key()
        connect_credential(self.env, self.google, credential, "Bot")
        connected = self._connected_credentials(self.google)
        self.assertEqual(len(connected), 2)
        self.assertEqual(set(connected.values()), {credential})

    def test_an_existing_company_connection_is_kept(self):
        connect(self.env, self.groq, key="company-key")
        before = self._connected_credentials(self.groq)
        with self.assertLogs(
            "odoo.addons.gateway_ml.tools.assistant_adoption", "WARNING"
        ):
            connect_credential(self.env, self.groq, self._loose_key(), "Bot")
        self.assertEqual(self._connected_credentials(self.groq), before)

    def test_a_key_bound_elsewhere_connects_nothing(self):
        credential = self._loose_key()
        credential.endpoint_id = self.env["integration.service"].search(
            [("code", "=", "openai")], limit=1
        )
        with self.assertLogs(
            "odoo.addons.gateway_ml.tools.assistant_adoption", "WARNING"
        ):
            connect_credential(self.env, self.groq, credential, "Bot")
        self.assertFalse(any(self._connected_credentials(self.groq).values()))

    def test_absent_columns_adopt_nothing(self):
        adopt_assistant_columns(self.env, "res.partner", "nothing")
