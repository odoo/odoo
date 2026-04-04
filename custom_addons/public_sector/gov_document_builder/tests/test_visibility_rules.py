import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestConditionalVisibility(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Visibilidade Teste",
                "code": "visibility_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Visibilidade Teste",
                "code": "template_visibility_test",
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
        self.instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento com Visibilidade Condicional",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "process_id": self.process.id,
            }
        )
        self.renderer = self.env["gov.document.typst.renderer"]
        self.resolver = self.env["gov.document.context.resolver"]

    def _render_with_context(self, layout, context):
        self.instance.write({"layout_json": json.dumps(layout)})
        with patch.object(
            type(self.resolver),
            "resolve_instance_context",
            autospec=True,
            return_value=context,
        ):
            return self.renderer.render_instance(self.instance)

    def test_block_hidden_when_rule_not_satisfied(self):
        rendered = self._render_with_context(
            [
                {
                    "id": "conditional_deficit",
                    "type": "conditional",
                    "sequence": 10,
                    "visibility_rule": "reconciliation.deficit > 0",
                    "children": [
                        {
                            "id": "conditional_text",
                            "type": "richtext",
                            "sequence": 10,
                            "props": {"content": "Bloco de déficit"},
                        }
                    ],
                }
            ],
            {
                "process": {"number": "SEMSA-2026-001"},
                "reconciliation": {
                    "deficit": 0.0,
                    "superavit": 2500.0,
                    "situacao_conciliacao": "pendente",
                },
                "document": {},
                "institution": {},
            },
        )

        self.assertNotIn("Bloco de déficit", rendered)

    def test_block_visible_when_rule_satisfied(self):
        rendered = self._render_with_context(
            [
                {
                    "id": "conditional_deficit",
                    "type": "conditional",
                    "sequence": 10,
                    "visibility_rule": "reconciliation.deficit > 0",
                    "children": [
                        {
                            "id": "conditional_text",
                            "type": "richtext",
                            "sequence": 10,
                            "props": {"content": "Bloco de déficit"},
                        }
                    ],
                }
            ],
            {
                "process": {"number": "SEMSA-2026-001"},
                "reconciliation": {
                    "deficit": 1800.0,
                    "superavit": 0.0,
                    "situacao_conciliacao": "pendente",
                },
                "document": {},
                "institution": {},
            },
        )

        self.assertIn("Bloco de déficit", rendered)

    def test_empty_visibility_rule_always_renders(self):
        rendered = self._render_with_context(
            [
                {
                    "id": "conditional_default",
                    "type": "conditional",
                    "sequence": 10,
                    "children": [
                        {
                            "id": "conditional_text",
                            "type": "richtext",
                            "sequence": 10,
                            "props": {"content": "Conteúdo sempre visível"},
                        }
                    ],
                }
            ],
            {
                "process": {"number": "SEMSA-2026-001"},
                "document": {},
                "institution": {},
            },
        )

        self.assertIn("Conteúdo sempre visível", rendered)

    def test_exists_operator_with_non_empty_value(self):
        result = self.resolver.evaluate_visibility_rule(
            "execution.ordens_fornecimento_count exists",
            {
                "execution": {
                    "ordens_fornecimento_count": 3,
                }
            },
        )

        self.assertTrue(result)

    def test_not_exists_operator_with_none_value(self):
        result = self.resolver.evaluate_visibility_rule(
            "auction.fornecedor not_exists",
            {
                "auction": {}
            },
        )

        self.assertTrue(result)

    def test_invalid_visibility_rule_fails_open_and_logs_warning(self):
        with self.assertLogs("odoo.addons.gov_document_builder", level="WARNING") as captured:
            result = self.resolver.evaluate_visibility_rule(
                "regra_invalida",
                {
                    "reconciliation": {
                        "situacao_conciliacao": "pendente",
                    }
                },
            )

        self.assertTrue(result)
        self.assertTrue(
            any("visibility_rule=regra_invalida" in message for message in captured.output)
        )
