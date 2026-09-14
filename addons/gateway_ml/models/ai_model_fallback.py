from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AIModelFallback(models.Model):
    _name = "gateway.ml.model.fallback"
    _description = "AI Model Fallback Hop"
    _order = "model_id, sequence, id"

    model_id = fields.Many2one(
        comodel_name="gateway.ml.model",
        index=True,
        required=True,
        ondelete="cascade",
        help="Model whose failure sends the request down this hop",
    )
    sequence = fields.Integer(default=10)
    fallback_id = fields.Many2one(
        comodel_name="gateway.ml.model",
        index=True,
        required=True,
        ondelete="cascade",
        help="Model tried when the one before it in the chain fails",
    )

    _hop_uniq = models.Constraint(
        "unique(model_id, fallback_id)",
        "A model lists each fallback once.",
    )

    @api.constrains("model_id", "fallback_id")
    def _check_fallback_id(self) -> None:
        for hop in self:
            if hop.fallback_id == hop.model_id:
                raise ValidationError(
                    self.env._(
                        "%(model)s cannot fall back to itself: the hop would repeat "
                        "the request that just failed.",
                        model=hop.model_id.display_name,
                    )
                )
            if hop.model_id.has_timestamps and not hop.fallback_id.has_timestamps:
                raise ValidationError(
                    self.env._(
                        "%(fallback)s cannot answer for %(model)s: it returns no "
                        "timestamps, and a caller of %(model)s may need them.",
                        fallback=hop.fallback_id.display_name,
                        model=hop.model_id.display_name,
                    )
                )
            if not hop.fallback_id._can_stand_in_for(hop.model_id):
                raise ValidationError(
                    self.env._(
                        "%(fallback)s cannot answer for %(model)s: its kind is "
                        "%(kind)s.",
                        fallback=hop.fallback_id.display_name,
                        kind=hop.fallback_id.kind,
                        model=hop.model_id.display_name,
                    )
                )
