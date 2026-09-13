from odoo import fields, models


class ResPartnerAttribute(models.Model):
    _name = "res.partner.attribute"
    _inherit = ["mixin.attribute", "mixin.score.catalog"]
    _description = "Contact Attribute"
    _attribute_line_model = "res.partner.attribute.line"
    _score_catalog_fields = ("aggregation_mode", "value_type", "active")

    value_ids = fields.One2many(
        comodel_name="res.partner.attribute.value",
        inverse_name="attribute_id",
        string="Values",
    )
    aggregation_mode = fields.Selection(
        selection=[
            ("sum", "Sum of values"),
            ("max", "Highest value"),
            ("none", "Not scored"),
        ],
        default="sum",
        required=True,
        help="How the selected values of this attribute contribute to the "
        "partner score: added together, only the highest one, or excluded. "
        "An excluded attribute, and any attribute whose values are all worth "
        "zero, is left out of the ceiling entirely and produces no row in the "
        "partner's score breakdown -- the captured values are kept, they are "
        "simply not explained there.",
    )
