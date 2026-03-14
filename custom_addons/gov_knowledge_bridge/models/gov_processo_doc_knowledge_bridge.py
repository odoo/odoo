import html
import re

from odoo import fields, models
from odoo.exceptions import UserError


class GovProcessoDocKnowledgeBridge(models.Model):
    _inherit = "gov.processo.doc"

    _HTML_TAG_RE_KNOWLEDGE = re.compile(r"<[^>]+>")

    knowledge_article_ids = fields.Many2many(
        "document.page",
        "gov_processo_doc_knowledge_article_rel",
        "doc_id",
        "article_id",
        string="Paginas de Conhecimento",
    )
    knowledge_article_count = fields.Integer(
        string="Qtd. Paginas de Conhecimento",
        compute="_compute_knowledge_article_count",
    )

    def _auto_init(self):
        self.env.cr.execute(
            """
            CREATE TABLE IF NOT EXISTS gov_processo_doc_knowledge_article_rel (
                doc_id integer NOT NULL,
                article_id integer NOT NULL
            )
            """
        )
        result = super()._auto_init()
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS gov_processo_doc_knowledge_article_rel_uniq
                ON gov_processo_doc_knowledge_article_rel (doc_id, article_id)
            """
        )
        return result

    def _compute_knowledge_article_count(self):
        for rec in self:
            rec.knowledge_article_count = len(rec.knowledge_article_ids)

    def _get_or_create_default_knowledge_category(self):
        self.ensure_one()
        company = self.processo_id.ug_id
        Page = self.env["document.page"]
        category = Page.search(
            [
                ("type", "=", "category"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
            ],
            order="company_id desc, id",
            limit=1,
        )
        if category:
            return category
        return Page.create(
            {
                "name": f"GOV - Documentos ({company.name})",
                "type": "category",
                "company_id": company.id,
            }
        )

    def action_open_knowledge_articles(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Conhecimento - {self.name}",
            "res_model": "document.page",
            "view_mode": "list,form",
            "domain": [("id", "in", self.knowledge_article_ids.ids)],
            "context": {
                "default_company_id": self.processo_id.ug_id.id,
                "default_type": "content",
            },
        }

    def action_create_knowledge_article(self):
        self.ensure_one()
        category = self._get_or_create_default_knowledge_category()
        title = f"Doc {self.name} - {self.processo_id.name or ''}".strip(" -")
        intro_html = (
            "<p><strong>Documento:</strong> "
            f"{html.escape(self.name or '')}</p>"
            "<p><strong>Processo:</strong> "
            f"{html.escape(self.processo_id.name or '')}</p>"
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Nova Pagina de Conhecimento",
            "res_model": "document.page",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_name": title,
                "default_type": "content",
                "default_parent_id": category.id,
                "default_company_id": self.processo_id.ug_id.id,
                "default_content": intro_html,
                "default_processo_doc_ids": [(6, 0, [self.id])],
                "default_processo_ids": [(6, 0, [self.processo_id.id])],
            },
        }

    def _plain_text_from_knowledge_html(self, html_text):
        text = self._HTML_TAG_RE_KNOWLEDGE.sub(" ", html_text or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def action_sync_knowledge_to_ai_memory(self):
        self.ensure_one()
        if not self.knowledge_article_ids:
            raise UserError("Nenhum artigo Knowledge vinculado ao documento.")

        Memory = self.env["gov.ai.memory"]
        created = 0
        updated = 0

        for article in self.knowledge_article_ids:
            plain = self._plain_text_from_knowledge_html(article.content or "")
            if not plain:
                continue
            vals = {
                "name": f"Conhecimento: {article.name}",
                "company_id": self.processo_id.ug_id.id,
                "source_type": "outro",
                "source_model": "document.page",
                "source_res_id": article.id,
                "tags": f"document_page,processo:{self.processo_id.name or ''},doc:{self.doc_type}",
                "content_text": plain,
            }
            existing = Memory.search(
                [
                    ("company_id", "=", self.processo_id.ug_id.id),
                    ("source_model", "=", "document.page"),
                    ("source_res_id", "=", article.id),
                ],
                limit=1,
            )
            if existing:
                existing.write(vals)
                updated += 1
            else:
                Memory.create(vals)
                created += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Knowledge sincronizado",
                "message": f"Memórias criadas: {created} | atualizadas: {updated}",
                "type": "success",
            },
        }
