from datetime import datetime, timedelta
from itertools import combinations

from odoo import fields
from odoo.addons.test_event_full.tests.common import TestEventFullCommon
from odoo.tests.common import users


class TestWebsiteEvent(TestEventFullCommon):

    @users('user_event_web_manager')
    def test_seo_data(self):
        """Test SEO data for submenus on event website page"""

        # Create an event
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'booth_menu': True,
            'exhibitor_menu': True,
            'community_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })

        self.assertFalse(event.website_meta_title, 'Event should initially have no meta title')
        event.write({
            'website_meta_title': 'info',
        })
        self.assertTrue(event.website_meta_title, 'Event should have a meta title after writing')

        self.check_seo_data_booth(event)
        self.check_seo_data_exhibitor(event)
        self.check_seo_data_community(event)
        self.check_seo_data_track(event)
        self.check_seo_data_agenda(event)
        self.check_seo_data_track_proposal(event)

    def check_seo_data_booth(self, event):
        view = event.booth_menu_ids.view_id
        self.assertFalse(view.website_meta_title, 'Get a booth page should initially have no meta title')
        view.write({
            'website_meta_title': 'Booth',
        })
        self.assertTrue(view.website_meta_title, 'Get a booth page should have a meta title after writing')

    def check_seo_data_exhibitor(self, event):
        view = event.exhibitor_menu_ids.view_id
        self.assertFalse(view.website_meta_title, 'Exhibitors page should initially have no meta title')
        view.write({
            'website_meta_title': 'exhibitors',
        })
        self.assertTrue(view.website_meta_title, 'Exhibitors page should have a meta title after writing')

    def check_seo_data_community(self, event):
        view = event.community_menu_ids.view_id
        self.assertFalse(view.website_meta_title, 'Community page should initially have no meta title')
        view.write({
            'website_meta_title': 'community',
        })
        self.assertTrue(view.website_meta_title, 'Community page should have a meta title after writing')

    def check_seo_data_track(self, event):
        view = event.track_menu_ids.filtered(lambda menu: menu.menu_id.name == 'Talks').view_id
        self.assertFalse(view.website_meta_title, 'Talks page should initially have no meta title')
        view.write({
            'website_meta_title': 'talks',
        })
        self.assertTrue(view.website_meta_title, 'Talks page should have a meta title after writing')

    def check_seo_data_agenda(self, event):
        view = event.track_menu_ids.filtered(lambda menu: menu.menu_id.name == 'Agenda').view_id
        self.assertFalse(view.website_meta_title, 'Agenda page should initially have no meta title')
        view.write({
            'website_meta_title': 'agenda',
        })
        self.assertTrue(view.website_meta_title, 'Agenda page should have a meta title after writing')

    def check_seo_data_track_proposal(self, event):
        view = event.track_proposal_menu_ids.view_id
        self.assertFalse(view.website_meta_title, 'Talk Proposals page should initially have no meta title')
        view.write({
            'website_meta_title': 'talk proposals',
        })
        self.assertTrue(view.website_meta_title, 'Talk Proposals page should have a meta title after writing')
