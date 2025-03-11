from odoo import api, fields, models


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate property types"
    _order = "name"

    name = fields.Char(required=True)
    _sql_constraints = [
        ("unique_type", "unique(name)", "A property type name must be unique")
    ]
    property_ids = fields.One2many("estate_property_type_line", "property_type_id")
    sequence = fields.Integer(
        "Sequence", default=1, help="Used to order stages. Lower is better."
    )
    offer_ids = fields.One2many(
        "estate.property.offer", "property_type_id", string="Offers"
    )
    offer_count = fields.Integer(compute="_compute_offer_count")

    @api.depends("offer_ids")
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)


class EstatePropertyTypeModelLine(models.Model):
    _name = "estate_property_type_line"
    _description = "Estate property type line"

    property_type_id = fields.Many2one("estate.property.type", ondelete="cascade")
    name = fields.Char(required=True)
    expected_price = fields.Float()
    status = fields.Selection(
        [
            ("new", "New"),
            ("sold", "Sold"),
        ],
        default="new",
        string="Status",
    )
