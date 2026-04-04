import json

from odoo.tests.common import TransactionCase


class TestGovDocumentTypstRenderer(TransactionCase):
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
        self.renderer = self.env["gov.document.typst.renderer"]

    def _create_instance(self, layout, process=None):
        vals = {
            "name": "Documento Renderer",
            "document_type_id": self.document_type.id,
            "template_id": self.template.id,
            "layout_json": json.dumps(layout),
        }
        if process:
            vals["process_id"] = process.id
        return self.env["gov.document.instance"].create(vals)

    def test_render_instance_includes_typst_preamble(self):
        instance = self._create_instance(
            [
                {"id": "h1", "type": "heading1", "sequence": 10, "props": {"text": "DFD"}},
                {"id": "txt", "type": "richtext", "sequence": 20, "props": {"content": "Texto livre"}},
                {"id": "sig", "type": "signature", "sequence": 30, "props": {}},
            ]
        )

        rendered = self.renderer.render_instance(instance)

        self.assertIn("#show: semsa_doc", rendered)
        self.assertIn("Texto livre", rendered)
        self.assertIn("#signature_block", rendered)

    def test_unknown_node_generates_fallback_comment(self):
        instance = self._create_instance(
            [
                {"id": "unk", "type": "bloco_desconhecido", "sequence": 10, "props": {}},
            ]
        )

        rendered = self.renderer.render_instance(instance)

        self.assertIn("// [bloco não renderizado: bloco_desconhecido]", rendered)

    def test_legal_basis_block_renders_base_legal_box(self):
        instance = self._create_instance(
            [
                {"id": "law", "type": "legal_basis", "sequence": 10, "props": {}},
            ]
        )

        rendered = self.renderer.render_instance(instance)

        self.assertIn("#base_legal_box", rendered)

    def test_conditional_node_is_hidden_when_visibility_rule_fails(self):
        instance = self._create_instance(
            [
                {
                    "id": "cond",
                    "type": "conditional",
                    "sequence": 10,
                    "visibility_rule": "reconciliation.deficit > 0",
                    "children": [
                        {
                            "id": "inner",
                            "type": "richtext",
                            "sequence": 10,
                            "props": {"content": "Bloco condicional visível"},
                        }
                    ],
                },
            ]
        )

        rendered = self.renderer.render_instance(instance)

        self.assertNotIn("Bloco condicional visível", rendered)

    def test_conditional_node_renders_children_when_visibility_rule_matches(self):
        process = self.env["gov.processo"].create(
            {
                "subject": "Aquisição de materiais",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        self.env["gov.processo.dotacao"].create(
            {
                "processo_id": process.id,
                "programa": "10",
                "acao": "2064",
                "natureza_despesa": "3.3.90.39",
                "fonte_recurso": "100",
                "valor_estimado": 150000,
                "exercicio": 2026,
                "reservado": True,
            }
        )
        instance = self._create_instance(
            [
                {
                    "id": "cond",
                    "type": "conditional",
                    "sequence": 10,
                    "visibility_rule": "reconciliation.situacao_conciliacao == pendente",
                    "children": [
                        {
                            "id": "inner",
                            "type": "richtext",
                            "sequence": 10,
                            "props": {"content": "Conciliação pendente identificada"},
                        }
                    ],
                },
            ],
            process=process,
        )

        rendered = self.renderer.render_instance(instance)

        self.assertIn("Conciliação pendente identificada", rendered)
