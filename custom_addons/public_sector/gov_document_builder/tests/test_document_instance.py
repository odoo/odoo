import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.gov_document_builder.controllers import document_builder_controller as controller_module
from odoo.tests.common import TransactionCase


class TestGovDocumentInstance(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Instância Teste",
                "code": "instance_type_test",
            }
        )
        self.template_layout = json.dumps(
            [
                {"id": "h1", "type": "heading1", "sequence": 10, "props": {"text": "Documento"}},
                {"id": "rt1", "type": "richtext", "sequence": 20, "props": {"content": "Conteúdo base"}},
            ]
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Instância Teste",
                "code": "template_instance_test",
                "document_type_id": self.document_type.id,
                "layout_schema_json": self.template_layout,
            }
        )

    def test_create_instance_from_template_loads_layout_json(self):
        controller = controller_module.DocumentBuilderController()
        fake_request = SimpleNamespace(env=self.env)

        with patch.object(controller_module, "request", fake_request):
            result = controller.create_from_template(self.document_type.code)

        instance = self.env["gov.document.instance"].browse(result["document_id"])
        self.assertTrue(instance.exists())
        self.assertEqual(instance.template_id, self.template)
        self.assertEqual(instance.document_type_id, self.document_type)
        self.assertEqual(instance.layout_json, self.template_layout)

    def test_action_approve_updates_state_and_creates_version(self):
        instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento em Aprovação",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "layout_json": self.template_layout,
            }
        )
        instance.write({"typst_source": "#show: semsa_doc(title: \"Documento\")"})

        instance.action_approve()

        self.assertEqual(instance.state, "approved")
        self.assertEqual(instance.version_count, 1)
        self.assertEqual(instance.version_ids[:1].change_summary, "Aprovação")

    def test_created_version_stores_typst_snapshot(self):
        instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento Versionado",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "layout_json": self.template_layout,
            }
        )
        expected_typst = "#show: semsa_doc(title: \"Versão\")\nConteúdo"
        instance.write({"typst_source": expected_typst})

        version = instance._create_version("Snapshot manual")

        self.assertEqual(version.document_instance_id, instance)
        self.assertEqual(version.typst_source, expected_typst)
        self.assertEqual(version.layout_json, self.template_layout)

    def test_create_instance_from_template_sets_gov_processo_many2one(self):
        process = self.env["gov.processo"].create(
            {
                "subject": "Aquisição de testes laboratoriais",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        controller = controller_module.DocumentBuilderController()
        fake_request = SimpleNamespace(env=self.env)

        with patch.object(controller_module, "request", fake_request):
            result = controller.create_from_template(
                self.document_type.code,
                process_id=process.id,
            )

        instance = self.env["gov.document.instance"].browse(result["document_id"])

        self.assertEqual(instance.process_id, process)
