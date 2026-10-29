# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EstatePropertyType(models.Model):
    """The kind of property (house, apartment, ...), configured by the agency."""

    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    # `sequence` is set by dragging the handle in the list view; the name breaks ties
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    property_ids = fields.One2many(
        string="Properties", comodel_name="estate.property", inverse_name="property_type_id"
    )
    offer_ids = fields.One2many(
        string="Offers", comodel_name="estate.property.offer", inverse_name="property_type_id"
    )
    offer_count = fields.Integer(string="Offer Count", compute="_compute_offer_count")

    _unique_name = models.Constraint(
        "UNIQUE(name)", "A property type with this name already exists."
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("offer_ids")
    def _compute_offer_count(self):
        # A single grouped query counts the offers of all types, instead of one query per type
        offer_counts = dict(
            self.env["estate.property.offer"]._read_group(
                domain=[("property_type_id", "in", self.ids)],
                groupby=["property_type_id"],
                aggregates=["__count"],
            )
        )
        for property_type in self:
            property_type.offer_count = offer_counts.get(property_type, 0)
