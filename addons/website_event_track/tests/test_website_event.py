# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon
from odoo.tests.common import users


class TestEventWebsiteTrack(TestWebsiteEventCommon):

    def _get_menus(self):
        return super(TestEventWebsiteTrack, self)._get_menus() | set(['Community', 'Talks', 'Agenda', 'Talk Proposals'])

    @users('user_eventmanager')
    def test_create_menu(self):
        event = self.env['event.event'].create({
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
        })

        self._assert_website_menus(event)

    @users('user_event_web_manager')
    def test_menu_management_frontend(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })
        self.assertTrue(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event)

        introduction_menu = event.menu_id.child_id.filtered(lambda menu: menu.name == 'Introduction')
        introduction_menu.unlink()
        self._assert_website_menus(event, set(['Location', 'Register', 'Community', 'Talks', 'Agenda', 'Talk Proposals']))

        menus = event.menu_id.child_id.filtered(lambda menu: menu.name in ['Agenda', 'Talk Proposals'])
        menus.unlink()
        self.assertTrue(event.website_track)
        self.assertFalse(event.website_track_proposal)

        menus = event.menu_id.child_id.filtered(lambda menu: menu.name in ['Talks'])
        menus.unlink()
        self.assertFalse(event.website_track)
        self.assertFalse(event.website_track_proposal)

        self._assert_website_menus(event, set(['Location', 'Register', 'Community']))

        event.write({'website_track_proposal': True})
        self.assertFalse(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, set(['Location', 'Register', 'Community', 'Talk Proposals']))

        event.write({'website_track': True})
        self.assertTrue(event.website_track)
        self.assertTrue(event.website_track_proposal)
        self._assert_website_menus(event, set(['Location', 'Register', 'Community', 'Talks', 'Agenda', 'Talk Proposals']))

    @users('user_eventmanager')
    def test_write_menu(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': False,
        })
        self.assertFalse(event.menu_id)
        event.write({
            'website_menu': True,
            'community_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })
        self._assert_website_menus(event)
