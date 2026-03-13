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
        self.assertIn("numero_processo_externo", template.latex_template)
        self.assertIn("numero_processo_externo", template.parameter_spec_json)
