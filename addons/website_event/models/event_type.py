from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    website_menu = fields.Boolean(string="Display a dedicated menu on Website")
    community_menu = fields.Boolean(
        compute="_compute_community_menu",
        store=True,
        readonly=False,
        help="Display community tab on website",
    )

    @api.depends("website_menu")
    def _compute_community_menu(self):
        for event_type in self:
            event_type.community_menu = event_type.website_menu
