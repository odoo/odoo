# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventWebsiteTrack(OnlineEventCase):

    def _get_menus(self):
        return super(TestEventWebsiteTrack, self)._get_menus() | set(['Talks', 'Agenda', 'Talk Proposals'])

    @users('user_eventmanager')
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
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register', 'Community'], menus_out=['Talks', 'Agenda', 'Talk Proposals'])

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

        introduction_menu = event.menu_id.child_id.filtered(lambda menu: menu.name == 'Introduction')
        introduction_menu.unlink()
        self._assert_website_menus(event, ['Location', 'Register', 'Community', 'Talks', 'Agenda', 'Talk Proposals'], menus_out=["Introduction"])

        menus = event.menu_id.child_id.filtered(lambda menu: menu.name in ['Agenda', 'Talk Proposals'])
        menus.unlink()
        self.assertTrue(event.website_track)
        self.assertFalse(event.website_track_proposal)

        menus = event.menu_id.child_id.filtered(lambda menu: menu.name in ['Talks'])
        menus.unlink()
        self.assertFalse(event.website_track)
        self.assertFalse(event.website_track_proposal)

        self._assert_website_menus(event, ['Location', 'Register', 'Community'], menus_out=["Introduction", "Talks", "Agenda", "Talk Proposals"])

        event.write({'website_track_proposal': True})
        self.assertFalse(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, ['Location', 'Register', 'Community', 'Talk Proposals'], menus_out=["Introduction", "Talks", "Agenda"])

        event.write({'website_track': True})
        self.assertTrue(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, ['Location', 'Register', 'Community', 'Talks', 'Agenda', 'Talk Proposals'], menus_out=["Introduction"])
