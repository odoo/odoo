from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    exhibitor_menu = fields.Boolean(
        string="Showcase Exhibitors",
        compute="_compute_exhibitor_menu",
        store=True,
        readonly=False,
        help="Display exhibitors on website, in the footer of every page of the event.",
    )

    @api.depends("website_menu")
    def _compute_exhibitor_menu(self):
        for event_type in self:
            event_type.exhibitor_menu = event_type.website_menu
