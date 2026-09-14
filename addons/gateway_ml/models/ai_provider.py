from typing import Any

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools.ai_clients import get_ai_client
from ..tools.provider_assistant import ProviderAssistant


class AIProvider(models.Model):
    _name = "gateway.ml.provider"
    _description = "AI Provider Configuration"
    _inherits = {"integration.service": "endpoint_id"}
    _order = "sequence, name"

    endpoint_id = fields.Many2one(
        comodel_name="integration.service",
        required=True,
        ondelete="cascade",
        help="Underlying API service configuration",
    )

    has_vision = fields.Boolean(
        compute="_compute_capabilities",
        store=True,
        readonly=True,
        help="At least one active model of this provider reads images",
    )
    has_embeddings = fields.Boolean(
        default=False,
        help="Vendor offers an embedding model. No client in this module reaches "
        "one, so this is asserted per vendor rather than derived from a model.",
    )
    has_audio = fields.Boolean(
        compute="_compute_capabilities",
        store=True,
        readonly=True,
        help="At least one active model of this provider handles audio",
    )
    has_free_tier = fields.Boolean(
        default=False,
        help="Provider offers a free tier or trial",
    )
    free_tier_limit = fields.Integer(
        help="Monthly request limit for free tier (if applicable)"
    )

    reliability_rating = fields.Selection(
        selection=[
            ("1", "Low"),
            ("2", "Medium-Low"),
            ("3", "Medium"),
            ("4", "Medium-High"),
            ("5", "High"),
        ],
        default="3",
        help="Service reliability and uptime rating (1-5 scale)",
    )

    best_for_tag_ids = fields.Many2many(
        comodel_name="ai.use.case.tag",
        relation="ai_provider_use_case_rel",
        column1="provider_id",
        column2="tag_id",
        help="Use cases this provider excels at (e.g., vision, reasoning, speed)",
    )

    model_ids = fields.One2many(
        comodel_name="gateway.ml.model",
        inverse_name="provider_id",
        help="Models reachable through this provider",
    )
    service_ids = fields.One2many(
        comodel_name="gateway.ml.provider.service",
        inverse_name="provider_id",
        string="Operations",
        help="What this provider can be asked to do, and through which service, wire "
        "and path each operation goes.",
    )
    default_model_id = fields.Many2one(
        comodel_name="gateway.ml.model",
        domain="[('provider_id', '=', id)]",
        ondelete="set null",
        help="Model a request runs on when the caller names none",
    )

    @api.depends("model_ids.has_vision", "model_ids.kind", "model_ids.active")
    def _compute_capabilities(self) -> None:
        for record in self:
            live = record.model_ids.filtered("active")
            record.has_vision = any(live.mapped("has_vision"))
            record.has_audio = "audio" in live.mapped("kind")

    @api.depends("name", "code", "default_model_id.code")
    def _compute_display_name(self) -> None:
        for record in self:
            parts: list[str] = [record.name or ""]
            if record.code:
                parts.append(f"[{record.code}]")
            if record.default_model_id.code:
                parts.append(f"({record.default_model_id.code})")
            record.display_name = " ".join(parts)

    @api.constrains("default_model_id")
    def _check_default_model_id(self) -> None:
        for record in self:
            default = record.default_model_id
            if default and default.provider_id != record:
                raise ValidationError(
                    self.env._(
                        "%(model)s is served by %(owner)s, so it cannot be the "
                        "default model of %(provider)s.",
                        model=default.display_name,
                        owner=default.provider_id.display_name,
                        provider=record.display_name,
                    )
                )

    def _service_for(self, operation):
        self.check_singleton()
        service = self.service_ids.filtered(lambda row: row.operation == operation)
        if not service:
            raise UserError(
                self.env._(
                    "%(provider)s does not offer %(operation)s.",
                    provider=self.display_name,
                    operation=operation,
                )
            )
        return service

    def _assistant(self, model=None, company_id=None):
        return ProviderAssistant(self, model=model, company_id=company_id)

    def _get_ai_client(self, company_id=None):
        self.check_singleton()
        client = get_ai_client(
            self.env,
            self.code,
            company_id=company_id or self.env.company.id,
        )
        if client is None:
            raise UserError(
                self.env._(
                    "Provider %(provider)s carries no operation on its own service "
                    "over a wire a client speaks.",
                    provider=self.code,
                ),
            )
        return client

    def action_view_request_logs(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Request Logs - %(provider)s", provider=self.name),
            "type": "ir.actions.act_window",
            "res_model": "integration.exchange",
            "view_mode": "list,form",
            "domain": [
                ("channel_id", "=", f"integration.service,{self.endpoint_id.id}"),
                ("direction", "=", "outbound"),
            ],
        }
