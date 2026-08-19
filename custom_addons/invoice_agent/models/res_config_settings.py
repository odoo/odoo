"""Admin settings for the invoice-agent extraction service.

The AI is now reached over HTTP as a standalone FastAPI service
(ADR-003). Three settings configure that service-to-service boundary:

* ``invoice_agent_llm_service_url`` — the base URL of ``invoice-ai``,
  normally the compose service name on the internal bridge network
  (``http://invoice-ai:8000``).
* ``invoice_agent_jwt_secret`` — the shared HS256 secret. Must equal the
  service's ``INVOICE_AI_JWT_SECRET`` or every call is rejected with 401.
* ``invoice_agent_confidence_threshold`` — the global routing threshold
  (inherited from the pre-HTTP milestone).

All three live in ``ir.config_parameter`` (``config_parameter=``) and are
never committed to source.
"""

from odoo import fields, models

from .llm_service import (
    AUTO_FILL_THRESHOLD_PARAM,
    CONFIDENCE_THRESHOLD_PARAM,
    DEFAULT_AUTO_FILL_THRESHOLD,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_REVIEW_THRESHOLD,
    DEFAULT_RAG_ENABLED,
    JWT_SECRET_PARAM,
    LLM_SERVICE_URL_PARAM,
    RAG_ENABLED_PARAM,
    REVIEW_THRESHOLD_PARAM,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_agent_llm_service_url = fields.Char(
        string="LLM Service URL",
        config_parameter=LLM_SERVICE_URL_PARAM,
        default="http://invoice-ai:8000",
        help="Base URL of the invoice-ai FastAPI service (ADR-003). Defaults "
        "to the compose service name on the internal bridge network.",
    )
    invoice_agent_jwt_secret = fields.Char(
        string="JWT Secret",
        config_parameter=JWT_SECRET_PARAM,
        help="Shared HS256 secret minting the service-to-service JWT. Must "
        "match the invoice-ai container's INVOICE_AI_JWT_SECRET. Never "
        "committed to git.",
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
    invoice_agent_auto_fill_threshold = fields.Float(
        string="Auto-Fill Threshold",
        config_parameter=AUTO_FILL_THRESHOLD_PARAM,
        default=DEFAULT_AUTO_FILL_THRESHOLD,
        digits=(3, 2),
        help="Confidence above this value (0..1) auto-fills the GL account "
        "on invoice lines and marks the bill ready for posting. Default 0.90.",
    )
    invoice_agent_review_threshold = fields.Float(
        string="Review Threshold",
        config_parameter=REVIEW_THRESHOLD_PARAM,
        default=DEFAULT_REVIEW_THRESHOLD,
        digits=(3, 2),
        help="Confidence below this value (0..1) flags the bill as "
        "'needs_human'. Between this and the Auto-Fill threshold, bills "
        "land in the review kanban column. Default 0.60.",
    )
    invoice_agent_rag_enabled = fields.Boolean(
        string="RAG Validation Enabled",
        config_parameter=RAG_ENABLED_PARAM,
        default=DEFAULT_RAG_ENABLED,
        help="When enabled, validated invoices go through the two-stage "
        "RAG retrieval + Claude validation pipeline. Disable (kill switch) "
        "to fall back to extraction-only mode.",
    )

    def set_values(self):
        res = super().set_values()
        # The routing compute cannot depend on ir.config_parameter inside
        # @api.depends, so after saving thresholds, re-run the compute on
        # every AI-processed move to move bills between Auto / Needs Review
        # / Needs Human immediately.
        if (
            self.invoice_agent_confidence_threshold
            or self.invoice_agent_auto_fill_threshold
            or self.invoice_agent_review_threshold
        ):
            moves = self.env["account.move"].search(
                [("ai_extraction_status", "in", ("extracted", "failed"))],
            )
            if moves:
                moves._compute_confidence_score()
                self.env["account.move"].flush_model()
        return res
