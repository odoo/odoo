from odoo import api, fields, models


class EventTypeBooth(models.Model):
    _name = "event.type.booth"
    _description = "Event Booth Template"

    def _default_booth_category_id(self):
        """Assign booth category by default if only one exists"""
        category_id = self.env["event.booth.category"].search([])
        if category_id and len(category_id) == 1:
            return category_id

    name = fields.Char(
        translate=True,
        required=True,
    )
    event_type_id = fields.Many2one(
        comodel_name="event.type",
        string="Event Category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    booth_category_id = fields.Many2one(
        comodel_name="event.booth.category",
        default=_default_booth_category_id,
        index=True,
        required=True,
        ondelete="restrict",
    )

    @api.model
    def _get_event_booth_fields_whitelist(self):
        return ["name", "booth_category_id"]
