from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventSeoData(OnlineEventCase):

    @users('user_event_web_manager')
    def test_seo_data_track(self):
        """Test SEO data for event and talks, talk proposals and agenda page"""

        # Create an event
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
        })

        self.assertFalse(event.website_meta_title, "Event should initially have no meta title")
        event.write({
            'website_meta_title': "info",
        })
        self.assertTrue(event.website_meta_title, "Event should have a meta title after writing")

        view_model_track = self.env['ir.ui.view'].search([('name', '=', 'Talks TestEvent')])
        self.assertFalse(view_model_track.website_meta_title, "Talks page should initially have no meta title")
        view_model_track.write({
            'website_meta_title': "talks",
        })
        self.assertTrue(view_model_track.website_meta_title, "Talks page should have a meta title after writing")
        self.assertNotEqual(event.website_meta_title, view_model_track.website_meta_title, "Event and Talks page should have different meta titles")

        view_model_agenda = self.env['ir.ui.view'].search([('name', '=', 'Agenda TestEvent')])
        self.assertFalse(view_model_agenda.website_meta_title, "Agenda page should initially have no meta title")
        view_model_agenda.write({
            'website_meta_title': "agenda",
        })
        self.assertTrue(view_model_agenda.website_meta_title, "Agenda page should have a meta title after writing")
        self.assertNotEqual(event.website_meta_title, view_model_agenda.website_meta_title, "Event and Agenda page should have different meta titles")

        view_model_track_proposal = self.env['ir.ui.view'].search([('name', '=', 'Talk Proposals TestEvent')])
        self.assertFalse(view_model_track_proposal.website_meta_title, "Talk Proposals page should initially have no meta title")
        view_model_track_proposal.write({
            'website_meta_title': "talk proposals",
        })
        self.assertTrue(view_model_track_proposal.website_meta_title, "Talk Proposals page should have a meta title after writing")
        self.assertNotEqual(event.website_meta_title, view_model_track_proposal.website_meta_title, "Event and Talk Proposals page should have different meta titles")

        self.assertNotEqual(view_model_track.website_meta_title, view_model_agenda.website_meta_title, "Talks and Agenda page should have different meta titles")
        self.assertNotEqual(view_model_track.website_meta_title, view_model_track_proposal.website_meta_title, "Talks and Talk Proposals page should have different meta titles")
        self.assertNotEqual(view_model_agenda.website_meta_title, view_model_track_proposal.website_meta_title, "Agenda and Talk Proposals page should have different meta titles")
