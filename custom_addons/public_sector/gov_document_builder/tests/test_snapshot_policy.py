import json

from odoo.tests.common import TransactionCase


class TestSnapshotPolicy(TransactionCase):
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
                "name": "SEMSA-2026-001",
                "subject": "Aquisição de medicamentos essenciais para UBS",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        self.env["gov.processo.parametro"].create(
            [
                {
                    "processo_id": self.process.id,
                    "key": "modalidade",
                    "name": "Modalidade da contratação",
                    "section": "required_by_law",
                    "fase": 2,
                    "value_type": "string",
                    "value_text": "Pregão Eletrônico",
                },
                {
                    "processo_id": self.process.id,
                    "key": "hipotese_dispensa",
                    "name": "Hipótese de dispensa",
                    "section": "required_by_law",
                    "fase": 1,
                    "value_type": "string",
                    "value_text": "Não se aplica",
                },
            ]
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

    def _approve_and_get_version(self):
        self.instance.action_approve()
        return self.instance.version_ids[:1]

    def test_version_snapshot_excludes_dynamic_namespaces(self):
        version = self._approve_and_get_version()

        snapshot_context = json.loads(version.resolved_context_json)

        self.assertNotIn("budget", snapshot_context)
        self.assertNotIn("execution", snapshot_context)
        self.assertNotIn("reconciliation", snapshot_context)

    def test_version_snapshot_includes_immutable_namespaces(self):
        version = self._approve_and_get_version()

        snapshot_context = json.loads(version.resolved_context_json)

        self.assertIn("process", snapshot_context)
        self.assertIn("legal", snapshot_context)
        self.assertEqual(snapshot_context["process"]["name"], "SEMSA-2026-001")
        self.assertEqual(
            snapshot_context["process"]["subject"],
            "Aquisição de medicamentos essenciais para UBS",
        )
        self.assertEqual(snapshot_context["legal"]["modalidade"], "Pregão Eletrônico")
        self.assertEqual(snapshot_context["legal"]["hipotese_dispensa"], "Não se aplica")

    def test_version_dynamic_namespaces_field_lists_excluded_keys(self):
        version = self._approve_and_get_version()

        dynamic_namespaces = json.loads(version.dynamic_namespaces_json or "[]")

        self.assertIn("budget", dynamic_namespaces)
        self.assertIn("execution", dynamic_namespaces)

    def test_render_version_resolves_budget_in_realtime(self):
        version = self._approve_and_get_version()

        self.dotacao.write({"valor_estimado": 175000})

        rendered = self.renderer.render_version(version)

        self.assertIn("175.000,00", rendered)
        self.assertNotIn("150.000,00", rendered)
