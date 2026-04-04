import json

from odoo.tests.common import TransactionCase


class TestGovDocumentSnapshotPolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Snapshot Teste",
                "code": "snapshot_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Snapshot Teste",
                "code": "template_snapshot_test",
                "document_type_id": self.document_type.id,
            }
        )
        self.process = self.env["gov.processo"].create(
            {
                "subject": "Aquisição de insumos hospitalares",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        self.env["gov.processo.parametro"].create(
            {
                "processo_id": self.process.id,
                "key": "modalidade",
                "name": "Modalidade da contratação",
                "section": "required_by_law",
                "fase": 2,
                "value_type": "string",
                "value_text": "Pregão Eletrônico",
            }
        )
        self.dotacao = self.env["gov.processo.dotacao"].create(
            {
                "processo_id": self.process.id,
                "programa": "10",
                "acao": "2064",
                "natureza_despesa": "3.3.90.39",
                "fonte_recurso": "100",
                "valor_estimado": 150000,
                "exercicio": 2026,
                "reservado": True,
            }
        )
        self.instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento Snapshot",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "process_id": self.process.id,
                "layout_json": json.dumps(
                    [
                        {
                            "id": "budget_field",
                            "type": "process_field",
                            "sequence": 10,
                            "props": {"label": "Empenhado"},
                            "binding": {
                                "source": "budget",
                                "path": "valor_empenhado",
                                "transform": "currency_br",
                            },
                        }
                    ]
                ),
            }
        )
        self.renderer = self.env["gov.document.typst.renderer"]

    def test_create_version_persists_only_snapshot_namespaces(self):
        version = self.instance._create_version("Snapshot semântico")

        snapshot_context = json.loads(version.resolved_context_json)
        dynamic_namespaces = json.loads(version.dynamic_namespaces_json or "[]")

        self.assertIn("process", snapshot_context)
        self.assertIn("legal", snapshot_context)
        self.assertNotIn("budget", snapshot_context)
        self.assertNotIn("execution", snapshot_context)
        self.assertNotIn("reconciliation", snapshot_context)
        self.assertEqual(snapshot_context["process"]["subject"], self.process.subject)
        self.assertEqual(snapshot_context["legal"]["modalidade"], "Pregão Eletrônico")
        self.assertIn("budget", dynamic_namespaces)
        self.assertIn("execution", dynamic_namespaces)
        self.assertIn("reconciliation", dynamic_namespaces)
        self.assertNotIn("process", dynamic_namespaces)

    def test_render_version_rehydrates_dynamic_budget_namespace(self):
        version = self.instance._create_version("Snapshot com orçamento")

        self.dotacao.write({"valor_estimado": 175000})

        rendered = self.renderer.render_version(version)

        self.assertIn("175.000,00", rendered)
        self.assertNotIn("150.000,00", rendered)

        version.action_rerender()

        self.assertIn("175.000,00", version.typst_source)
