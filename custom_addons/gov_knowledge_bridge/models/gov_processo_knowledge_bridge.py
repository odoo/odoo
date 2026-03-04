import html
import re

from odoo import fields, models
from odoo.exceptions import UserError


class GovProcessoKnowledgeBridge(models.Model):
    _inherit = "gov.processo"

    _HTML_TAG_RE = re.compile(r"<[^>]+>")

    knowledge_article_ids = fields.Many2many(
        "knowledge.article",
        "gov_processo_knowledge_article_rel",
        "processo_id",
        "article_id",
        string="Artigos Knowledge",
    )
    knowledge_article_count = fields.Integer(
        string="Qtd. Artigos Knowledge",
        compute="_compute_knowledge_article_count",
    )

    def _compute_knowledge_article_count(self):
        for rec in self:
            rec.knowledge_article_count = len(rec.knowledge_article_ids)

    def action_open_knowledge_articles(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Knowledge - {self.name}",
            "res_model": "knowledge.article",
            "view_mode": "list,form",
            "domain": [("id", "in", self.knowledge_article_ids.ids)],
            "context": {"default_company_id": self.ug_id.id},
        }

    def action_create_knowledge_article(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Novo Artigo Knowledge",
            "res_model": "knowledge.article",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_name": f"Processo {self.name} - {self.subject or ''}".strip(" -"),
                "default_category": "workspace",
                "default_company_id": self.ug_id.id,
                "default_processo_ids": [(6, 0, [self.id])],
            },
        }

    def _plain_text_from_html(self, html_text):
        text = self._HTML_TAG_RE.sub(" ", html_text or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def action_sync_knowledge_to_ai_memory(self):
        self.ensure_one()
        if not self.knowledge_article_ids:
            raise UserError("Nenhum artigo Knowledge vinculado ao processo.")

        Memory = self.env["gov.ai.memory"]
        created = 0
        updated = 0

        for article in self.knowledge_article_ids:
            plain = self._plain_text_from_html(article.body or "")
            if not plain:
                continue
            vals = {
                "name": f"Knowledge: {article.name}",
                "company_id": self.ug_id.id,
                "source_type": "outro",
                "source_model": "knowledge.article",
                "source_res_id": article.id,
                "tags": f"knowledge,processo:{self.name or ''}",
                "content_text": plain,
            }
            existing = Memory.search(
                [
                    ("company_id", "=", self.ug_id.id),
                    ("source_model", "=", "knowledge.article"),
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
