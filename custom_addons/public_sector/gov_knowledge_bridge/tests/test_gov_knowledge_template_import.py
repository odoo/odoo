import base64

from odoo.tests.common import TransactionCase


class TestGovKnowledgeTemplateImport(TransactionCase):
    def test_import_template_from_knowledge_page(self):
        article = self.env["document.page"].create(
            {
                "name": "Modelo DFD",
                "type": "content",
                "content": r"""
<p>\documentclass{article}</p>
<p>\begin{document}</p>
<p>DFD {{numero_processo_externo}}</p>
<p>\end{document}</p>
                """,
            }
        )

        wizard = self.env["gov.knowledge.template.import.wizard"].create(
            {
                "article_id": article.id,
                "name": "Template via Knowledge",
                "doc_type": "dfd",
                "process_type": "compras_servicos",
                "process_scope": "all",
                "fase": 0,
                "source_mode": "page_content",
                "output_format": "latex",
            }
        )

        action = wizard.action_import()
        template = self.env["gov.ai.template"].browse(action["res_id"])

        self.assertEqual(template.knowledge_article_id, article)
        self.assertEqual(template.source_input_format, "html")
        self.assertIn("numero_processo_externo", template.latex_template)
        self.assertIn("numero_processo_externo", template.parameter_spec_json)

    def test_import_template_from_typst_upload(self):
        article = self.env["document.page"].create(
            {
                "name": "Modelo Typst",
                "type": "content",
                "content": "<p>Artigo-base</p>",
            }
        )
        typst_content = "= Documento\n\nNumero: {{numero_processo}}\n"
        wizard = self.env["gov.knowledge.template.import.wizard"].create(
            {
                "article_id": article.id,
                "name": "Template Typst via Upload",
                "doc_type": "dfd",
                "process_type": "compras_servicos",
                "process_scope": "all",
                "fase": 0,
                "source_mode": "upload",
                "output_format": "typst",
                "upload_file": base64.b64encode(typst_content.encode("utf-8")).decode("ascii"),
                "upload_filename": "modelo.typ",
            }
        )

        action = wizard.action_import()
        template = self.env["gov.ai.template"].browse(action["res_id"])

        self.assertEqual(template.source_input_format, "typst")
        self.assertIn("numero_processo", template.typst_template)
        self.assertTrue(template.latex_template)
        self.assertIn("numero_processo", template.parameter_spec_json)

    def test_import_template_from_csv_upload(self):
        article = self.env["document.page"].create(
            {
                "name": "Planilha Referência",
                "type": "content",
                "content": "<p>Planilha</p>",
            }
        )
        csv_content = "item,descricao,valor\n1,Detergente,25.00\n"
        wizard = self.env["gov.knowledge.template.import.wizard"].create(
            {
                "article_id": article.id,
                "name": "Template CSV",
                "doc_type": "dfd",
                "process_type": "compras_servicos",
                "process_scope": "all",
                "fase": 0,
                "source_mode": "upload",
                "output_format": "latex",
                "upload_file": base64.b64encode(csv_content.encode("utf-8")).decode("ascii"),
                "upload_filename": "itens.csv",
            }
        )

        action = wizard.action_import()
        template = self.env["gov.ai.template"].browse(action["res_id"])

        self.assertEqual(template.source_input_format, "csv")
        self.assertIn("Detergente", template.latex_template)
        self.assertIn("longtable", template.latex_template)
