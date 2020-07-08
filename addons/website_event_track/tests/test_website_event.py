# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon
from odoo.tests.common import users


class TestEventWebsiteTrack(TestWebsiteEventCommon):

    def _get_menus(self):
        return super(TestEventWebsiteTrack, self)._get_menus() | set(['Talks', 'Agenda', 'Talk Proposals'])

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
            'website_track': True,
            'website_track_proposal': True,
        })

        self._assert_website_menus(event)

    @users('user_eventmanager')
    def test_write_menu(self):
        event = self.env['event.event'].browse(self.event_0.id)
        self.assertFalse(event.menu_id)
        event.write({
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })
        self._assert_website_menus(event)
