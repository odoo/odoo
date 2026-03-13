import os
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import AI_PROVIDER_SELECTION


class GovAiProviderConfig(models.Model):
    _name = "gov.ai.provider.config"
    _description = "Configuração de Provedor de IA por UG"
    _order = "company_id, sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(string="Padrão da UG", default=False)
    company_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    provider = fields.Selection(
        AI_PROVIDER_SELECTION,
        string="Provedor IA",
        required=True,
        default="ollama",
    )
    model_name = fields.Char(
        string="Modelo",
        required=True,
        default="llama3.2:1b",
    )
    endpoint_url = fields.Char(
        string="Endpoint URL",
        help="Opcional para OpenAI/Claude/Hugging Face. Obrigatório para Ollama custom.",
        default=lambda self: os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/") + "/api/generate"
    )
    api_key = fields.Char(
        string="API Key",
        help="Use apenas para provedores externos. Para Ollama/odoo_chat pode ficar vazio.",
    )
    temperature = fields.Float(default=0.2)
    max_tokens = fields.Integer(default=2000)
    timeout_seconds = fields.Integer(default=90)
    memory_top_k = fields.Integer(
        string="Memórias por Prompt",
        default=5,
        help="Quantidade máxima de blocos de memória de UG injetados no prompt.",
    )
    notes = fields.Text(string="Observações")

    @api.onchange("provider")
    def _onchange_provider_defaults(self):
        for rec in self:
            if rec.provider == "openai":
                rec.model_name = rec.model_name or "gpt-4o-mini"
                rec.endpoint_url = rec.endpoint_url or "https://api.openai.com/v1/chat/completions"
            elif rec.provider == "anthropic":
                rec.model_name = rec.model_name or "claude-3-5-sonnet-latest"
                rec.endpoint_url = rec.endpoint_url or "https://api.anthropic.com/v1/messages"
            elif rec.provider == "huggingface":
                rec.model_name = rec.model_name or "mistralai/Mistral-7B-Instruct-v0.3"
                rec.endpoint_url = rec.endpoint_url or "https://api-inference.huggingface.co/models"
            elif rec.provider == "ollama":
                rec.model_name = rec.model_name or "llama3.2:1b"
                ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
                rec.endpoint_url = rec.endpoint_url or f"{ollama_host}/api/generate"
            else:
                rec.model_name = rec.model_name or "odoo_chat_local"
                rec.endpoint_url = False

    @api.constrains("is_default", "company_id", "provider")
    def _check_single_default_per_provider(self):
        for rec in self:
            if not rec.is_default:
                continue
            duplicate = self.search(
                [
                    ("id", "!=", rec.id),
                    ("company_id", "=", rec.company_id.id),
                    ("provider", "=", rec.provider),
                    ("is_default", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    f"Já existe um provedor padrão {rec.provider} para esta UG: {duplicate.name}."
                )

    @api.model
    def get_active_for_company(self, company_id):
        if not company_id:
            return self.search([("active", "=", True)], order="is_default desc, sequence, id", limit=1)
        config = self.search(
            [
                ("company_id", "=", company_id),
                ("active", "=", True),
                ("is_default", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )
        if config:
            return config
        return self.search(
            [
                ("company_id", "=", company_id),
                ("active", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )
