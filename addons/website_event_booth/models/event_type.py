from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    booth_menu = fields.Boolean(
        string="Booths on Website",
        compute="_compute_booth_menu",
        store=True,
        readonly=False,
    )

    @api.depends("website_menu")
    def _compute_booth_menu(self):
        for event_type in self:
            event_type.booth_menu = event_type.website_menu
