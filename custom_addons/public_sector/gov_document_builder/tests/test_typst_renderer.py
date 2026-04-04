import json

from odoo.tests.common import TransactionCase


class TestTypstRenderer(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Renderer Teste",
                "code": "renderer_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Renderer Teste",
                "code": "template_renderer_test",
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
        self.env["gov.processo.dotacao"].create(
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
                "name": "Documento Renderer",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "process_id": self.process.id,
            }
        )
        self.renderer = self.env["gov.document.typst.renderer"]

    def _set_layout(self, layout):
        self.instance.write({"layout_json": json.dumps(layout)})

    def test_renderer_produces_nonempty_typst(self):
        self._set_layout(
            [
                {
                    "id": "h1",
                    "type": "heading1",
                    "sequence": 10,
                    "props": {"text": "DFD"},
                },
                {
                    "id": "txt",
                    "type": "richtext",
                    "sequence": 20,
                    "props": {"content": "Texto livre"},
                },
            ]
        )

        rendered = self.renderer.render_instance(self.instance)

        self.assertTrue(rendered)
        self.assertIn('#import "base.typ": semsa_doc', rendered)

    def test_conditional_block_suppressed_in_output(self):
        self._set_layout(
            [
                {
                    "id": "subject",
                    "type": "process_field",
                    "sequence": 10,
                    "props": {"label": "Objeto"},
                    "binding": {
                        "source": "process",
                        "path": "subject",
                    },
                },
                {
                    "id": "deficit",
                    "type": "rich_text",
                    "sequence": 20,
                    "visibility_rule": "reconciliation.deficit > 0",
                    "props": {"content": "Bloco com déficit"},
                },
            ]
        )

        rendered = self.renderer.render_instance(self.instance)

        self.assertIn("Aquisição de medicamentos essenciais para UBS", rendered)
        self.assertNotIn("Bloco com déficit", rendered)

    def test_renderer_handles_missing_block_type_gracefully(self):
        self._set_layout(
            [
                {
                    "id": "missing",
                    "type": "bloco_inexistente",
                    "sequence": 10,
                    "props": {},
                }
            ]
        )

        rendered = self.renderer.render_instance(self.instance)

        self.assertIn("// [bloco não renderizado: bloco_inexistente]", rendered)

    def test_currency_transformer_formats_value_as_brl(self):
        self._set_layout(
            [
                {
                    "id": "budget_currency",
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
        )

        rendered = self.renderer.render_instance(self.instance)

        self.assertIn("150.000,00", rendered)
