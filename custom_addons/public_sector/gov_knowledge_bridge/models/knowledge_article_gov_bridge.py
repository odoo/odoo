from odoo import fields, models


class DocumentPageGovBridge(models.Model):
    _inherit = "document.page"

    processo_ids = fields.Many2many(
        "gov.processo",
        "gov_processo_knowledge_article_rel",
        "article_id",
        "processo_id",
        string="Processos GOV",
    )
    processo_doc_ids = fields.Many2many(
        "gov.processo.doc",
        "gov_processo_doc_knowledge_article_rel",
        "article_id",
        "doc_id",
        string="Documentos GOV",
    )
    processo_count = fields.Integer(
        string="Qtd. Processos GOV",
        compute="_compute_gov_counts",
    )
    processo_doc_count = fields.Integer(
        string="Qtd. Documentos GOV",
        compute="_compute_gov_counts",
    )
    gov_template_ids = fields.One2many(
        "gov.ai.template",
        "knowledge_article_id",
        string="Modelos GOV",
    )
    gov_template_count = fields.Integer(
        string="Qtd. Modelos GOV",
        compute="_compute_gov_counts",
    )

    def _compute_gov_counts(self):
        for rec in self:
            rec.processo_count = len(rec.processo_ids)
            rec.processo_doc_count = len(rec.processo_doc_ids)
            rec.gov_template_count = len(rec.gov_template_ids)

    def action_open_gov_processos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Processos GOV - {self.name}",
            "res_model": "gov.processo",
            "view_mode": "list,kanban,form",
            "domain": [("id", "in", self.processo_ids.ids)],
        }

    def action_open_gov_documentos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Documentos GOV - {self.name}",
            "res_model": "gov.processo.doc",
            "view_mode": "list,form",
            "domain": [("id", "in", self.processo_doc_ids.ids)],
        }

    def action_open_gov_templates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Modelos GOV - {self.name}",
            "res_model": "gov.ai.template",
            "view_mode": "list,form",
            "domain": [("knowledge_article_id", "=", self.id)],
            "context": {
                "default_knowledge_article_id": self.id,
            },
        }

    def action_import_gov_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Importar Modelo GOV",
            "res_model": "gov.knowledge.template.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_article_id": self.id,
                "default_name": self.name,
            },
        }
