from odoo import api, fields, models


class EventTrackLocation(models.Model):
    _name = 'event.track.location'
    _description = 'Event Track Location'
    _order = 'sequence, id'

    name = fields.Char('Location', required=True)
    sequence = fields.Integer(default=10, help='Define the order in which the location will appear on "Agenda" page')
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
