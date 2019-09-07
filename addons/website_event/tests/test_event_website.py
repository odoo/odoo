from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.event.tests.common import TestEventCommon


class TestEventWebsiteHelper(TestEventCommon):
    def _get_menus(self):
        return set(['Introduction', 'Location', 'Register'])

    def _assert_website_menus(self, event):
        self.assertTrue(event.menu_id)

        menus = self.env['website.menu'].search([('parent_id', '=', event.menu_id.id)])
        self.assertEqual(len(menus), len(self._get_menus()))
        self.assertEqual(set(menus.mapped('name')), self._get_menus())


class TestEventWebsite(TestEventWebsiteHelper):

    def test_create_menu0(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'registration_ids': [(0, 0, {
                'partner_id': self.user_eventuser.partner_id.id,
            })],
            'website_menu': True,
        })

        self._assert_website_menus(event)

    def test_write_menu0(self):
        self.assertFalse(self.event_0.menu_id)
        self.event_0.website_menu = True
        self._assert_website_menus(self.event_0)
