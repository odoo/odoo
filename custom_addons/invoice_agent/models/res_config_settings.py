"""Admin settings for the invoice agent LLM service.

The API key is stored in ``ir.config_parameter`` through the
``config_parameter=`` attribute; it is never committed to source. The model
id defaults to the pinned ``claude-opus-4-8`` but can be overridden here
without a redeploy (the service reads ``invoice_agent.anthropic_model`` at
call time).
"""

from odoo import fields, models

from .llm_service import (
    CONFIDENCE_THRESHOLD_PARAM,
    DEFAULT_CONFIDENCE_THRESHOLD,
)


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
    invoice_agent_confidence_threshold = fields.Float(
        string="Auto-Approval Confidence Threshold",
        config_parameter=CONFIDENCE_THRESHOLD_PARAM,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        digits=(3, 2),
        help="Global confidence threshold (0..1) for routing AI-extracted "
        "bills into the Auto kanban column. Overrides the per-journal "
        "ai_min_confidence. Changeable at runtime — no redeploy needed; a "
        "lower value immediately moves pending low-confidence bills to "
        "review and vice-versa (the rollback path for a bad threshold).",
    )

    def set_values(self):
        res = super().set_values()
        # The routing compute cannot depend on ir.config_parameter inside
        # @api.depends, so after saving a threshold, re-run the compute on
        # every AI-processed move to move bills between Auto / Needs
        # Review immediately.
        if self.invoice_agent_confidence_threshold:
            moves = self.env["account.move"].search(
                [("ai_extraction_status", "in", ("extracted", "failed"))],
            )
            if moves:
                moves._compute_confidence_score()
                self.env["account.move"].flush_model()
        return res
