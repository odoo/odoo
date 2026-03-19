from odoo import fields, models
from odoo.tools.sql import column_exists, create_column


class GovAiTemplateKnowledgeBridge(models.Model):
    _inherit = "gov.ai.template"

    knowledge_article_id = fields.Many2one(
        "document.page",
        string="Artigo Knowledge",
        ondelete="set null",
        copy=False,
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "gov_ai_template", "knowledge_article_id"):
            create_column(self.env.cr, "gov_ai_template", "knowledge_article_id", "int4")

        result = super()._auto_init()
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS gov_ai_template_knowledge_article_id_idx
                ON gov_ai_template (knowledge_article_id)
            """
        )
        return result

    def action_open_knowledge_article(self):
        self.ensure_one()
        if not self.knowledge_article_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": f"Knowledge - {self.knowledge_article_id.name}",
            "res_model": "document.page",
            "res_id": self.knowledge_article_id.id,
            "view_mode": "form",
            "target": "current",
        }
