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

        # Run SEO tests and store view models for different pages
        view_model_booth = self.assert_seo_data(event, 'Get A Booth', 'booth')
        view_model_exhibitor = self.assert_seo_data(event, 'Exhibitors', 'exhibitors')
        view_model_community = self.assert_seo_data(event, 'Community', 'community')
        view_model_track = self.assert_seo_data(event, 'Talks', 'talks')
        view_model_agenda = self.assert_seo_data(event, 'Agenda', 'agenda')
        view_model_track_proposal = self.assert_seo_data(event, 'Talk Proposals', 'talk proposals')

        # SEO data test of submenus
        view_models = [
            (view_model_booth, 'Booth page'),
            (view_model_exhibitor, 'Exhibitor page'),
            (view_model_community, 'Community page'),
            (view_model_track, 'Talks page'),
            (view_model_agenda, 'Agenda page'),
            (view_model_track_proposal, 'Talk Proposals page')
        ]

        # Compare each view model with every other view model to ensure their meta titles are different
        for (model1, name1), (model2, name2) in combinations(view_models, 2):
            self.assertNotEqual(
                model1.website_meta_title,
                model2.website_meta_title,
                f'{name1} and {name2} should have different meta titles'
            )
