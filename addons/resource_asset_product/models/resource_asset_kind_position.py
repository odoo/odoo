from odoo import fields, models


class ResourceAssetKindPosition(models.Model):
    _name = "resource.asset.kind.position"
    _description = "Asset Part Position"
    _order = "kind_id, sequence, id"

    # FIELDS
    kind_id = fields.Many2one(
        comodel_name="resource.asset.kind",
        index=True,
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Part Category",
        help="A part installed here must belong to this category or one below it.",
    )
    expected_life_days = fields.Integer(
        string="Expected Life (Days)",
        help="A replacement at this position sooner than this is flagged.",
    )
    meter_kind = fields.Selection(
        selection="_selection_meter_kind",
        help="The asset meter the expected life is measured on.",
    )
    expected_life_meter = fields.Float(
        string="Expected Life (Meter)",
        help="A replacement at this position sooner than this distance on the meter is flagged.",
    )

    # CONSTRAINTS
    _kind_code_uniq = models.Constraint(
        "UNIQUE(kind_id, code)", "A position code is unique within its asset kind."
    )
    _expected_life_positive = models.Constraint(
        "CHECK(expected_life_days >= 0 AND expected_life_meter >= 0)",
        "An expected life cannot be negative.",
    )

    # HELPER METHODS
    def _selection_meter_kind(self):
        return self.env["resource.asset.meter"]._fields["kind"].selection
