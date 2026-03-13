from odoo import fields, models


class GovAiTemplateKnowledgeBridge(models.Model):
    _inherit = "gov.ai.template"

    knowledge_article_id = fields.Many2one(
        "document.page",
        string="Artigo Knowledge",
        ondelete="set null",
        copy=False,
    )

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
