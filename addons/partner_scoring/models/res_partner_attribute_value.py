from odoo import fields, models


class ResPartnerAttributeValue(models.Model):
    _name = "res.partner.attribute.value"
    _inherit = ["mixin.attribute.value", "mixin.score.catalog"]
    _description = "Contact Attribute Value"
    _order = "attribute_id, sequence, name"
    _score_weight_field = "score_value"
    _score_catalog_fields = ("score_value", "active", "attribute_id")

    attribute_id = fields.Many2one(
        comodel_name="res.partner.attribute",
        index=True,
        required=True,
        ondelete="cascade",
    )
    score_value = fields.Float(
        string="Score Points",
        default=0.0,
        help="Points this value contributes to the partner score, combined "
        "according to the attribute's aggregation mode.",
    )

    _score_value_not_negative = models.Constraint(
        "CHECK(score_value >= 0)",
        "A score weight cannot be negative: the ceiling only counts positive "
        "weights, so a penalty would lower a score against a denominator that "
        "never saw it.",
    )
