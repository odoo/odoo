from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    community_menu = fields.Boolean(
        "Community", compute="_compute_community_menu",
        readonly=False, store=True,
        help="Display the \"Rooms\" tab on website, redirecting to the leaderboard of the event.")

    @api.depends('website_menu')
    def _compute_community_menu(self):
        for event_type in self:
            event_type.community_menu = event_type.website_menu
