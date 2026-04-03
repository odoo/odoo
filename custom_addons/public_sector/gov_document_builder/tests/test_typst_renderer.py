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

    def _create_instance(self, layout):
        return self.env["gov.document.instance"].create(
            {
                "name": "Documento Renderer",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "layout_json": json.dumps(layout),
            }
        )

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
