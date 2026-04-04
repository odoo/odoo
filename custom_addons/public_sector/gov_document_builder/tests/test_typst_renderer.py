import json
from unittest.mock import patch

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

    def test_render_layout_filters_only_none_nodes(self):
        self._set_layout(
            [
                {
                    "id": "first",
                    "type": "richtext",
                    "sequence": 10,
                    "props": {"content": "Primeiro"},
                },
                {
                    "id": "second",
                    "type": "richtext",
                    "sequence": 20,
                    "props": {"content": "Segundo"},
                },
                {
                    "id": "third",
                    "type": "richtext",
                    "sequence": 30,
                    "props": {"content": "Terceiro"},
                },
            ]
        )

        with patch.object(
            type(self.renderer),
            "_render_preamble",
            autospec=True,
            return_value=[],
        ), patch.object(
            type(self.renderer),
            "_render_node",
            autospec=True,
            side_effect=["", None, "Conteúdo final"],
        ):
            rendered = self.renderer._render_layout(self.instance, self.instance.layout_json, {})

        self.assertEqual(rendered, "\n\n\nConteúdo final\n")

    def test_sumario_renderer_outputs_outline_with_title_and_depth(self):
        rendered = self.renderer._render_sumario(
            {
                "id": "toc",
                "type": "sumario",
                "props": {
                    "titulo": "Sumário",
                    "profundidade": 2,
                    "mostrar_numeros": True,
                },
            },
            {},
        )

        self.assertEqual(rendered, "#outline(title: [Sumário], depth: 2)")

    def test_sumario_renderer_hides_page_numbers_when_disabled(self):
        rendered = self.renderer._render_sumario(
            {
                "id": "toc",
                "type": "sumario",
                "props": {
                    "titulo": "Índice do Documento",
                    "profundidade": 1,
                    "mostrar_numeros": False,
                },
            },
            {},
        )

        self.assertIn("#set outline.entry(fill: none)", rendered)
        self.assertIn("it.indented(it.prefix(), it.body())", rendered)
        self.assertIn("#outline(title: [Índice do Documento], depth: 1)", rendered)
