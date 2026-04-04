import json
from unittest.mock import patch

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

    def test_contract_snapshot_keeps_static_fields_and_refreshes_dynamic_ones(self):
        resolver = self.env["gov.document.context.resolver"]
        self.instance.write(
            {
                "layout_json": json.dumps(
                    [
                        {
                            "id": "contract_total",
                            "type": "process_field",
                            "sequence": 10,
                            "props": {"label": "Valor contratado"},
                            "binding": {
                                "source": "contract",
                                "path": "valor_contratado",
                                "transform": "currency_br",
                            },
                        },
                        {
                            "id": "contract_balance",
                            "type": "process_field",
                            "sequence": 20,
                            "props": {"label": "Saldo restante"},
                            "binding": {
                                "source": "contract",
                                "path": "saldo_restante",
                                "transform": "currency_br",
                            },
                        },
                    ]
                )
            }
        )
        initial_context = json.loads(
            json.dumps(resolver.resolve_instance_context(self.instance), ensure_ascii=False)
        )
        initial_context["contract"] = {
            "valor_contratado": 17000.0,
            "numero_contrato": "023/2026",
            "data_inicio_vigencia": "2026-04-10",
            "data_fim_vigencia": "2027-04-10",
            "quantidade_aditivos": 1,
            "saldo_restante": 8500.0,
        }
        initial_context["reconciliation"] = resolver.compute_reconciliation_namespace(initial_context)

        updated_context = json.loads(json.dumps(initial_context, ensure_ascii=False))
        updated_context["contract"] = {
            "valor_contratado": 19000.0,
            "numero_contrato": "099/2026",
            "data_inicio_vigencia": "2026-06-01",
            "data_fim_vigencia": "2027-06-01",
            "quantidade_aditivos": 3,
            "saldo_restante": 4000.0,
        }
        updated_context["reconciliation"] = resolver.compute_reconciliation_namespace(updated_context)

        with patch.object(
            type(resolver),
            "resolve_instance_context",
            autospec=True,
            return_value=initial_context,
        ):
            version = self.instance._create_version("Snapshot híbrido de contrato")

        snapshot_context = json.loads(version.resolved_context_json or "{}")
        dynamic_namespaces = json.loads(version.dynamic_namespaces_json or "[]")

        self.assertIn("contract", snapshot_context)
        self.assertEqual(snapshot_context["contract"]["valor_contratado"], 17000.0)
        self.assertNotIn("saldo_restante", snapshot_context["contract"])
        self.assertNotIn("quantidade_aditivos", snapshot_context["contract"])
        self.assertIn("contract", dynamic_namespaces)

        with patch.object(
            type(resolver),
            "resolve_instance_context",
            autospec=True,
            return_value=updated_context,
        ):
            rendered = self.renderer.render_version(version)

        self.assertIn("17.000,00", rendered)
        self.assertIn("4.000,00", rendered)
        self.assertNotIn("19.000,00", rendered)
        self.assertNotIn("8.500,00", rendered)

    def test_render_version_resolves_budget_in_realtime(self):
        version = self._approve_and_get_version()

        self.dotacao.write({"valor_estimado": 175000})

        rendered = self.renderer.render_version(version)

        self.assertIn("175.000,00", rendered)
        self.assertNotIn("150.000,00", rendered)
