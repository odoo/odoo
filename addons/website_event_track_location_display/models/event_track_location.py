from odoo import api, fields, models


class EventTrackLocation(models.Model):
    _inherit = 'event.track.location'

    location_display_url = fields.Char("Location Display Link", compute='_compute_location_display_url')

    @api.depends_context('active_model', 'active_id')
    def _compute_location_display_url(self):
        event_id = (
            self.env.context.get('active_id')
            if self.env.context.get('active_model') == 'event.event'
            else False
        )
        if not event_id:
            self.location_display_url = False
            return
        for location in self:
            location.location_display_url = (
                f'/event/{event_id}/location-display/{location.id}'
                if location.id else False
            )
