from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    website_track = fields.Boolean(
        string="Tracks on Website",
        compute="_compute_website_track_menu_data",
        store=True,
        readonly=False,
    )
    website_track_proposal = fields.Boolean(
        string="Tracks Proposals on Website",
        compute="_compute_website_track_menu_data",
        store=True,
        readonly=False,
    )

    @api.depends("website_menu")
    def _compute_website_track_menu_data(self):
        for event_type in self:
            event_type.website_track = event_type.website_menu
            event_type.website_track_proposal = event_type.website_menu
