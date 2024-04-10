# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventWebsiteTrack(OnlineEventCase):

    def _get_menus(self):
        return super()._get_menus() | {'Talks'}

    @users('user_event_web_manager')
    def test_create_menu(self):
        vals = {
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'registration_ids': [(0, 0, {
                'partner_id': self.user_eventuser.partner_id.id,
                'name': 'test_reg',
            })],
            'website_menu': True,
            'community_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        }
        event = self.env['event.event'].create(vals)
        self._assert_website_menus(event)

        event.write({
            'website_track': False,
            'website_track_proposal': False,
        })
        self._assert_website_menus(event, ['Home', 'Community', 'Practical'], menus_out=['Talks'])

    @users('user_event_web_manager')
    def test_menu_management_frontend(self):
        vals = {
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        }
        event = self.env['event.event'].create(vals)
        self.assertTrue(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, self._get_menus())

        menus = event.menu_id.child_id
        home_menu = menus.filtered(lambda menu: menu.name == 'Home')
        home_menu.unlink()
        self._assert_website_menus(event, ['Talks', 'Community', 'Practical'], menus_out=['Home'])

        sub_menus = menus.child_id.filtered(lambda menu: menu.name in ['Agenda', 'Propose a talk'])
        sub_menus.unlink()
        self.assertTrue(event.website_track)
        self.assertFalse(event.website_track_proposal)

        talks_menu = menus.child_id.filtered(lambda menu: menu.name == 'Talks')
        talks_menu.unlink()
        self.assertFalse(event.website_track)
        self.assertFalse(event.website_track_proposal)

        self._assert_website_menus(event, ['Practical', 'Community'], menus_out=['Home', 'Talks'])

        event.write({'website_track': True})
        self.assertTrue(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, ['Practical', 'Community', 'Talks'], menus_out=['Home'])

        event.write({'website_track_proposal': False})
        self.assertTrue(event.website_track)
        self.assertFalse(event.website_track_proposal)
        self._assert_website_menus(event, ['Practical', 'Community', 'Talks'], menus_out=['Home'])
