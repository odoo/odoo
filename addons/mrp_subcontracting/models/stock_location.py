from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    subcontractor_ids = fields.One2many(
        comodel_name="res.partner",
        inverse_name="property_stock_subcontractor",
    )

    @api.constrains("usage", "location_id")
    def _check_subcontracting_location(self):
        for location in self:
            if location == location.company_id.subcontracting_location_id:
                raise ValidationError(
                    _("You cannot alter the company's subcontracting location")
                )
            if location.is_subcontract() and location.usage != "internal":
                raise ValidationError(
                    _(
                        "In order to manage stock accurately, subcontracting locations must be type Internal, linked to the appropriate company."
                    )
                )

    def _filtered_putaway_access(self):
        if self.env.user.partner_id.is_subcontractor:
            return self.sudo()
        else:
            return super()._filtered_putaway_access()

    def is_subcontract(self):
        subcontracting_location = self.company_id.subcontracting_location_id
        return subcontracting_location and self._is_child_of(subcontracting_location)
