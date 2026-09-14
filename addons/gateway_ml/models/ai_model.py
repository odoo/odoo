from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class AIModel(models.Model):
    _name = "gateway.ml.model"
    _inherit = ["mixin.catalog"]
    _description = "AI Model"
    _order = "provider_id, sequence, name"

    provider_id = fields.Many2one(
        comodel_name="gateway.ml.provider",
        index=True,
        required=True,
        ondelete="cascade",
        help="Vendor endpoint this model is reached through",
    )
    code = fields.Char(
        index=True,
        required=True,
        help="Identifier sent as the 'model' parameter on the wire",
    )
    kind = fields.Selection(
        selection=[
            ("chat", "Chat"),
            ("vision", "Vision"),
            ("audio", "Audio"),
            ("embedding", "Embedding"),
        ],
        default="chat",
        required=True,
        help="What this model is called for",
    )
    sequence = fields.Integer(default=10)

    has_vision = fields.Boolean(
        default=False,
        help="Can read images sent alongside the prompt",
    )
    has_timestamps = fields.Boolean(
        default=False,
        help="Says when each passage of a recording was spoken, which subtitles "
        "and a player need; a transcription model without it returns text alone",
    )
    supports_streaming = fields.Boolean(
        default=True,
        help="Supports streaming responses",
    )
    supports_function_calling = fields.Boolean(
        default=False,
        help="Supports function/tool calling",
    )
    max_tokens_param = fields.Selection(
        selection=[
            ("max_tokens", "max_tokens"),
            ("max_completion_tokens", "max_completion_tokens"),
        ],
        string="Output Cap Parameter",
        default="max_tokens",
        required=True,
        help="The body member this model reads its output cap from. OpenAI's "
        "reasoning models refuse max_tokens and want max_completion_tokens.",
    )
    min_max_tokens = fields.Integer(
        string="Minimum Output Cap",
        help="The smallest output cap worth sending: a model that reasons before it "
        "answers spends a small budget on reasoning and returns nothing.",
    )
    request_extra = fields.Json(
        string="Extra Request Members",
        help="Members sent in every request body to this model, such as a reasoning "
        "effort or a fixed temperature the vendor requires.",
    )
    sampling_params = fields.Boolean(
        string="Accepts Sampling Parameters",
        default=True,
        help="Accepts temperature, top_p and top_k. Anthropic's newest models "
        "reject them.",
    )
    forced_tool_choice = fields.Boolean(
        string="Accepts a Forced Tool",
        default=True,
        help="Accepts a tool_choice that forces a tool. A model that does not is "
        "asked for structured output through output_config instead.",
    )
    language_form_key = fields.Selection(
        selection=[("language", "language"), ("languages[]", "languages[]")],
        string="Language Form Key",
        default="language",
        required=True,
        help="The multipart form key a transcription model reads the language from.",
    )
    vocabulary_param = fields.Selection(
        selection=[("keyterm", "keyterm"), ("keywords", "keywords")],
        string="Vocabulary Parameter",
        help="The query parameter a Deepgram model reads boosted vocabulary from.",
    )
    max_context_window = fields.Integer(help="Maximum context window size in tokens")
    max_output_tokens = fields.Integer(
        help="Maximum number of output tokens per request"
    )

    cost_per_1m_input = fields.Float(
        digits=(12, 6),
        help="Cost per 1 million input tokens in USD",
    )
    cost_per_1m_output = fields.Float(
        digits=(12, 6),
        help="Cost per 1 million output tokens in USD",
    )
    cost_per_1m_image = fields.Float(
        digits=(12, 6),
        help="Cost per 1 million pixels for image processing",
    )
    cost_per_audio_minute = fields.Float(
        digits=(12, 6),
        help="Cost per minute of audio processing",
    )

    accuracy_rating = fields.Selection(
        selection=[
            ("1", "Low"),
            ("2", "Medium-Low"),
            ("3", "Medium"),
            ("4", "Medium-High"),
            ("5", "High"),
        ],
        default="3",
        help="Subjective accuracy rating (1-5 scale)",
    )
    speed_rating = fields.Selection(
        selection=[
            ("1", "Slow"),
            ("2", "Medium-Slow"),
            ("3", "Medium"),
            ("4", "Medium-Fast"),
            ("5", "Fast"),
        ],
        default="3",
        help="Response speed rating (1-5 scale)",
    )

    fallback_ids = fields.One2many(
        comodel_name="gateway.ml.model.fallback",
        inverse_name="model_id",
        string="Fallback Hops",
        help="Models to try, in this order, when this one fails. A hop may stay on "
        "this provider — a smaller model on a key you already hold — or cross to "
        "another. Hops archived or without a usable credential are skipped.",
    )
    fallback_model_ids = fields.Many2many(
        comodel_name="gateway.ml.model",
        compute="_compute_fallback_model_ids",
        inverse="_inverse_fallback_model_ids",
        help="The fallback hops' models, in chain order",
    )

    _code_uniq = models.Constraint(
        "unique(provider_id, code)",
        "A provider cannot serve the same model code twice!",
    )
    _name_src_uniq = name_uniq_index(
        "provider_id",
        message="This provider already has a model with that name.",
    )

    _PER_MINUTE_KINDS = ("audio",)

    _INTERCHANGEABLE_KINDS = ("chat", "vision")

    # A blended price weighs input three to one, the usual convention: extraction
    # and classification, what this module serves, read far more than they write.
    _INPUT_WEIGHT = 3

    @api.depends("name", "code")
    def _compute_display_name(self) -> None:
        for record in self:
            record.display_name = f"{record.name} [{record.code}]"

    @api.constrains("kind", "has_vision")
    def _check_vision_kind_reads_images(self) -> None:
        for record in self:
            if record.kind == "vision" and not record.has_vision:
                raise ValidationError(
                    self.env._(
                        "%(model)s is a vision model, so it must read images.",
                        model=record.display_name,
                    )
                )

    @api.depends("fallback_ids.sequence", "fallback_ids.fallback_id")
    def _compute_fallback_model_ids(self) -> None:
        for record in self:
            record.fallback_model_ids = record.fallback_ids.sorted(
                lambda hop: (hop.sequence, hop.id)
            ).fallback_id

    def _inverse_fallback_model_ids(self) -> None:
        for record in self:
            record.fallback_ids = [Command.clear()] + [
                Command.create({"fallback_id": model.id, "sequence": position})
                for position, model in enumerate(record.fallback_model_ids, start=1)
            ]

    def _can_stand_in_for(self, other) -> bool:
        self.check_singleton()
        if other.has_timestamps and not self.has_timestamps:
            return False
        return self.kind == other.kind or {self.kind, other.kind} <= set(
            self._INTERCHANGEABLE_KINDS
        )

    def _get_unit_cost(self) -> float:
        self.check_singleton()
        if self.kind in self._PER_MINUTE_KINDS:
            return self.cost_per_audio_minute
        weighted = [
            (weight, price)
            for weight, price in (
                (self._INPUT_WEIGHT, self.cost_per_1m_input),
                (1, self.cost_per_1m_output),
            )
            if price
        ]
        if not weighted:
            return 0.0
        return sum(weight * price for weight, price in weighted) / sum(
            weight for weight, _price in weighted
        )
