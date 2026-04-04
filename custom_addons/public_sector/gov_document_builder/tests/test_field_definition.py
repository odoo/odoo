from psycopg2 import IntegrityError
from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.gov_document_builder.controllers import document_builder_controller as controller_module
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestGovDocumentFieldDefinition(TransactionCase):
    def setUp(self):
        super().setUp()
        self.controller = controller_module.DocumentBuilderController()
        self.fake_request = SimpleNamespace(env=self.env)

    def test_display_path_is_computed_from_namespace_and_variable_key(self):
        definition = self.env["gov.document.field.definition"].create(
            {
                "name": "Campo de teste",
                "namespace": "process",
                "variable_key": "campo_teste_unico",
                "value_type": "text",
                "mutability_policy": "immutable",
            }
        )

        self.assertEqual(definition.display_path, "process.campo_teste_unico")

    def test_field_definitions_endpoint_filters_by_namespace(self):
        with patch.object(controller_module, "request", self.fake_request):
            result = self.controller.get_field_definitions(namespace="budget")

        self.assertTrue(result)
        self.assertTrue(all(item["namespace"] == "budget" for item in result))
        self.assertEqual(result[0]["variable_key"], "valor_empenhado")

    def test_duplicate_namespace_and_variable_key_raises_integrity_error(self):
        self.env["gov.document.field.definition"].create(
            {
                "name": "Campo duplicado base",
                "namespace": "process",
                "variable_key": "campo_unico_catalogo",
                "value_type": "text",
                "mutability_policy": "immutable",
            }
        )

        with mute_logger("odoo.sql_db"), self.cr.savepoint(), self.assertRaises(IntegrityError):
            self.env["gov.document.field.definition"].create(
                {
                    "name": "Campo duplicado conflito",
                    "namespace": "process",
                    "variable_key": "campo_unico_catalogo",
                    "value_type": "text",
                    "mutability_policy": "dynamic",
                }
            )

    def test_seeded_process_state_definition_is_dynamic(self):
        definition = self.env["gov.document.field.definition"].search(
            [
                ("namespace", "=", "process"),
                ("variable_key", "=", "state"),
            ],
            limit=1,
        )

        self.assertTrue(definition)
        self.assertEqual(definition.name, "Fase atual")
        self.assertEqual(definition.value_type, "text")
        self.assertEqual(definition.mutability_policy, "dynamic")
        self.assertEqual(definition.display_path, "process.state")

    def test_field_definitions_endpoint_returns_expected_payload_keys(self):
        with patch.object(controller_module, "request", self.fake_request):
            result = self.controller.get_field_definitions(namespace="reconciliation")

        self.assertTrue(result)
        self.assertEqual(
            set(result[0]),
            {
                "id",
                "name",
                "namespace",
                "variable_key",
                "value_type",
                "mutability_policy",
                "default_transformer",
                "example_value",
                "description",
                "display_path",
            },
        )
        self.assertTrue(all(item["namespace"] == "reconciliation" for item in result))
