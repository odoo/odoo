from odoo import api, fields, models
from odoo.exceptions import ValidationError

OPERATIONS = [
    ("chat", "Chat"),
    ("transcribe", "Transcribe"),
    ("transcribe_timed", "Transcribe with timestamps"),
    ("synthesize", "Synthesize speech"),
    ("embed", "Embed"),
]

WIRES = [
    ("openai_compatible", "OpenAI-compatible"),
    ("anthropic_messages", "Anthropic Messages"),
    ("gemini_native", "Gemini native"),
    ("deepgram", "Deepgram"),
]


class GatewayMlProviderService(models.Model):
    _name = "gateway.ml.provider.service"
    _description = "Machine Learning Provider Operation"
    _order = "provider_id, operation"

    provider_id = fields.Many2one(
        comodel_name="gateway.ml.provider",
        index=True,
        required=True,
        ondelete="cascade",
    )
    operation = fields.Selection(
        selection=OPERATIONS,
        required=True,
    )
    service_id = fields.Many2one(
        comodel_name="integration.service",
        string="Service",
        required=True,
        ondelete="restrict",
        help="The integration service this operation is sent through. A vendor may "
        "expose one operation on a different base URL than another: Gemini's chat "
        "speaks the OpenAI wire on one, its audio the native wire on another.",
    )
    wire = fields.Selection(
        selection=WIRES,
        required=True,
        help="The request and response shape this operation speaks.",
    )
    path = fields.Char(
        required=True,
        help="Path under the service's URL. `{model}` is replaced with the model code.",
    )
    model_id = fields.Many2one(
        comodel_name="gateway.ml.model",
        string="Default Model",
        ondelete="set null",
        help="The model this operation runs on when the caller names none.",
    )
    timeout = fields.Integer(
        help="Seconds to wait for the vendor's answer to this operation.",
    )
    voice = fields.Char(
        help="Voice a speech synthesis uses when the caller names none.",
    )
    formats = fields.Json(
        help="For speech synthesis: the vendor's name for each audio mimetype it can "
        "produce, as a mapping from mimetype to format.",
    )

    _operation_uniq = models.Constraint(
        "unique(provider_id, operation)",
        "A provider carries each operation once.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()
        return super().create(vals_list)

    def write(self, vals):
        if {"service_id", "wire", "provider_id"} & set(vals):
            self.env.registry.clear_cache()
        return super().write(vals)

    def unlink(self):
        self.env.registry.clear_cache()
        return super().unlink()

    @api.depends("provider_id", "operation")
    def _compute_display_name(self):
        labels = dict(OPERATIONS)
        for record in self:
            record.display_name = (
                f"{record.provider_id.name} · {labels.get(record.operation, '')}"
            )

    @api.constrains("model_id", "provider_id")
    def _check_model_belongs_to_provider(self):
        for record in self:
            if record.model_id and record.model_id.provider_id != record.provider_id:
                raise ValidationError(
                    self.env._(
                        "%(model)s is served by %(owner)s, not %(provider)s.",
                        model=record.model_id.display_name,
                        owner=record.model_id.provider_id.display_name,
                        provider=record.provider_id.display_name,
                    )
                )
