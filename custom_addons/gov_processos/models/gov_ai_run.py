from odoo import fields, models

from .constants import AI_PROVIDER_SELECTION


class GovAiRun(models.Model):
    _name = "gov.ai.run"
    _description = "Log de Execução de IA"
    _order = "create_date desc, id desc"

    name = fields.Char(default="Execução IA", required=True)
    company_id = fields.Many2one("res.company", required=True)
    processo_id = fields.Many2one("gov.processo")
    doc_id = fields.Many2one("gov.processo.doc")
    template_id = fields.Many2one("gov.ai.template")
    provider = fields.Selection(AI_PROVIDER_SELECTION, default="odoo_chat", required=True)
    model_name = fields.Char()
    status = fields.Selection(
        [
            ("success", "Sucesso"),
            ("error", "Erro"),
        ],
        required=True,
        default="success",
    )
    prompt_system = fields.Text()
    prompt_user = fields.Text()
    memory_snapshot = fields.Text(string="Memórias Injetadas")
    response_text = fields.Text()
    raw_response = fields.Text()
    error_message = fields.Text()
    duration_ms = fields.Integer()
    created_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
