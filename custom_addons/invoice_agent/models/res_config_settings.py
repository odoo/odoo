"""Admin settings for the invoice agent LLM service.

The API key is stored in ``ir.config_parameter`` through the
``config_parameter=`` attribute; it is never committed to source. The model
id defaults to the pinned ``claude-opus-4-8`` but can be overridden here
without a redeploy (the service reads ``invoice_agent.anthropic_model`` at
call time).
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_agent_anthropic_api_key = fields.Char(
        string="Anthropic API Key",
        config_parameter="invoice_agent.anthropic_api_key",
        help="Secret key for the Anthropic Messages API. Never committed to git.",
    )
    invoice_agent_anthropic_model = fields.Char(
        string="Anthropic Model",
        config_parameter="invoice_agent.anthropic_model",
        default="claude-opus-4-8",
        help="Model id used by the invoice.llm.service wrapper for extraction.",
    )
