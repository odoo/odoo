from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventSeoData(OnlineEventCase):

    @users('user_event_web_manager')
    def test_seo_data_exhibitor(self):
        """Test SEO data for event and exhibitors page"""

        # Create an event
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'exhibitor_menu': True,
        })

        self.assertFalse(event.website_meta_title, "Event should initially have no meta title")
        event.write({
            'website_meta_title': "info",
        })
        self.assertTrue(event.website_meta_title, "Event should have a meta title after writing")

        view_model = self.env['ir.ui.view'].search([('name', '=', 'Exhibitors TestEvent')])

        self.assertFalse(view_model.website_meta_title, "Exhibitors page should initially have no meta title")
        view_model.write({
            'website_meta_title': "exhibitors",
        })
        self.assertTrue(view_model.website_meta_title, "Exhibitors page should have a meta title after writing")

        self.assertNotEqual(event.website_meta_title, view_model.website_meta_title, "Event and Exhibitors page should have different meta titles")
