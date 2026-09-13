from odoo import api, fields, models


class EventTypeBooth(models.Model):
    _name = "event.type.booth"
    _description = "Event Booth Template"

    def _default_booth_category_id(self):
        """Assign booth category by default if only one exists"""
        category_id = self.env["event.booth.category"].search([])
        if category_id and len(category_id) == 1:
            return category_id

    name = fields.Char(required=True, translate=True)
    event_type_id = fields.Many2one(
        "event.type",
        string="Event Category",
        ondelete="cascade",
        required=True,
        index=True,
    )
    booth_category_id = fields.Many2one(
        "event.booth.category",
        index=True,
        default=_default_booth_category_id,
        ondelete="restrict",
        required=True,
    )

    @api.model
    def _get_event_booth_fields_whitelist(self):
        return ["name", "booth_category_id"]
