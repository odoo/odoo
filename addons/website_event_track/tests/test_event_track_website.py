from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.test_event_website import TestEventWebsiteHelper


class TestEventWebsiteTrack(TestEventWebsiteHelper):

    def _get_menus(self):
        return super(TestEventWebsiteTrack, self)._get_menus() | set(['Talks', 'Agenda', 'Talk Proposals'])

    def test_create_menu1(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'registration_ids': [(0, 0, {
                'partner_id': self.user_eventuser.partner_id.id,
            })],
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })

        self._assert_website_menus(event)

    def test_write_menu1(self):
        self.assertFalse(self.event_0.menu_id)
        self.event_0.write({
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })
        self._assert_website_menus(self.event_0)
