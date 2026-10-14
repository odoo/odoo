# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import BaseCase
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleEvent


class TestGoogleEvent(BaseCase):
    def test_google_event_readonly(self):
        event = GoogleEvent()
        with self.assertRaises(TypeError):
            event._items['foo'] = 'bar'
        with self.assertRaises(AttributeError):
            event._items.update({'foo': 'bar'})
        with self.assertRaises(TypeError):
            dict.update(event._items, {'foo': 'bar'})
