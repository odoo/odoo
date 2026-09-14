from odoo import fields, models


class IntegrationExchange(models.Model):
    _inherit = "integration.exchange"

    ml_model_id = fields.Many2one(
        comodel_name="gateway.ml.model",
        string="ML Model",
        index="btree_not_null",
        readonly=True,
        ondelete="set null",
        help="The model a machine learning vendor ran for this exchange, read from "
        "the request.",
    )
    ml_input_tokens = fields.Integer(
        string="Input Tokens",
        readonly=True,
        help="Tokens the vendor counted in, as its response reported them.",
    )
    ml_output_tokens = fields.Integer(
        string="Output Tokens",
        readonly=True,
        help="Tokens the vendor counted out, reasoning tokens included.",
    )
    ml_audio_seconds = fields.Float(
        string="Audio Seconds",
        readonly=True,
        help="Seconds of audio the vendor billed.",
    )
    ml_cost = fields.Float(
        string="Cost (USD)",
        digits=(16, 6),
        readonly=True,
        help="What the reported usage costs at the model row's prices when the "
        "exchange was recorded. Empty when the row carries no price.",
    )
