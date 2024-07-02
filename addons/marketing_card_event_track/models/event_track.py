from odoo import models


class EventTrack(models.Model):
    _inherit = 'event.track'

    def _marketing_card_allowed_field_paths(self):
        partner_allowed_paths = self.env['res.partner']._marketing_card_allowed_field_paths()
        return [
            'display_name', 'name',
            'event_id', 'event_id.name', 'event_id.display_name',
            'image', 'partner_id',
            'location_id', 'location_id.name', 'location_id.display_name',
            'date', 'date_end',
            'event_id', 'event_id.name', 'event_id.display_name'
        ] + [f'partner_id.{partner_path}' for partner_path in partner_allowed_paths]
