from odoo import fields, models


class SuiteDashboardAiProvider(models.Model):
    _name = "suite.dashboard.ai.provider"
    _description = "Suite Dashboard AI Provider"
    _order = "company_id, name, id"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    provider_type = fields.Selection(
        [
            ("openai", "OpenAI"),
            ("azure_openai", "Azure OpenAI"),
            ("ollama", "Ollama"),
        ],
        required=True,
        default="ollama",
    )
    endpoint = fields.Char()
    api_key = fields.Char(groups="base.group_system")
    model_name = fields.Char(required=True, default="qwen2.5:0.5b")
    timeout = fields.Integer(default=60)
    active = fields.Boolean(default=True)
