from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.gov_document_builder.controllers import document_builder_controller as controller_module
from odoo.tests.common import TransactionCase


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
