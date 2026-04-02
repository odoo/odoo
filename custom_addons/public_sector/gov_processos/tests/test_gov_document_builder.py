import json

from odoo.tests.common import TransactionCase


class TestGovDocumentBuilder(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Aquisição de medicamentos da atenção básica",
                "process_type": "contratacao_direta",
                "process_scope": "compras",
            }
        )
        self.doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "doc_type": "dfd",
                "name": "DFD Medicamentos",
                "dfd_area_requisitante": "Diretoria de Assistência Farmacêutica",
                "dfd_objeto": "<p>Aquisição de medicamentos essenciais.</p>",
                "dfd_justificativa": "<p>Reposição do estoque estratégico da SEMSA.</p>",
                "dfd_valor_estimado": 125000.5,
            }
        )
        self.template = self.env["gov.processo.doc.builder.template"].create(
            {
                "name": "Template Builder DFD Teste",
                "doc_type": "dfd",
                "process_type": "contratacao_direta",
                "process_scope": "compras",
                "sequence": 1,
                "block_payload_json": json.dumps(
                    [
                        {
                            "type": "titulo",
                            "content": {
                                "titulo": "DFD SEMSA",
                                "subtitulo": "{{process_subject}}",
                            },
                        },
                        {"type": "cabecalho_processo", "content": {}},
                        {"type": "quadro_resumo", "content": {"linhas": ""}},
                    ],
                    ensure_ascii=False,
                ),
            }
        )

    def test_builder_bootstrap_returns_context_and_template_blocks(self):
        payload = self.doc.action_builder_bootstrap()

        self.assertEqual(payload["doc"]["id"], self.doc.id)
        self.assertEqual(payload["record_context"]["record_model"], "gov.processo.doc")
        self.assertEqual(payload["record_context"]["process_subject"], self.processo.subject)
        self.assertEqual(
            payload["record_context"]["requesting_area"],
            "Diretoria de Assistência Farmacêutica",
        )
        self.assertEqual(
            payload["record_context"]["estimated_value_label"],
            "R$ 125.000,50",
        )
        self.assertEqual(payload["builder_template"]["id"], self.template.id)
        self.assertEqual(
            [block["type"] for block in payload["initial_blocks"]],
            ["titulo", "cabecalho_processo", "quadro_resumo"],
        )
        self.assertEqual(
            payload["initial_blocks"][0]["content"]["subtitulo"],
            self.processo.subject,
        )

    def test_builder_save_payload_persists_layout_and_typst(self):
        blocks = [
            {
                "id": "block_a",
                "type": "titulo",
                "label": "Título Principal",
                "editable": True,
                "content": {
                    "titulo": "DFD — Medicamentos",
                    "subtitulo": "Assistência farmacêutica 2026",
                },
            },
            {
                "id": "block_b",
                "type": "objeto",
                "label": "Objeto",
                "editable": True,
                "content": {"html": "<p>Compra de medicamentos.</p>"},
            },
            {
                "id": "block_c",
                "type": "justificativa",
                "label": "Justificativa",
                "editable": True,
                "content": {"html": "<p>Reposição da rede assistencial.</p>"},
            },
        ]

        response = self.doc.action_builder_save_payload(
            layout_payload=blocks,
            typst_source='#heading(level: 1)["DFD"]\nCompra de medicamentos.',
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["doc_id"], self.doc.id)
        self.assertEqual(response["doc_name"], "DFD — Medicamentos - Assistência farmacêutica 2026")
        self.assertTrue(response["typst_filename"].endswith(".typ"))
        self.assertIn("Compra de medicamentos.", self.doc.typst_source)
        self.assertEqual(self.doc.name, "DFD — Medicamentos - Assistência farmacêutica 2026")
        self.assertIn("Compra de medicamentos", self.doc.dfd_objeto)
        self.assertIn("Reposição da rede assistencial", self.doc.dfd_justificativa)
        saved_layout = json.loads(self.doc.layout_json or "[]")
        self.assertEqual([item["type"] for item in saved_layout], ["titulo", "objeto", "justificativa"])
