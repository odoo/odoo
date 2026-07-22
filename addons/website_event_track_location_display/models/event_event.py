from odoo import fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    location_display_background = fields.Image("Location Display Background")
    location_display_upcoming_track_count = fields.Selection(
        selection=[('2', "2"), ('3', "3"), ('4', "4"), ('5', "5")],
        string="Coming Up Sessions",
        default='3',
        required=True,
    )

    def action_view_track_locations(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('website_event_track.action_event_track_location')
        location_list_view = self.env.ref('website_event_track_location_display.view_event_location_list_from_event', raise_if_not_found=False)
        action.update({
            'name': self.env._("Track Locations"),
            'domain': [('id', 'in', self.track_ids.location_id.ids)],
            'views': [
                (location_list_view.id if location_list_view else False, 'list'),
                (False, 'form'),
            ],
        })
        return action
