# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch

from odoo.addons.website_event_exhibitor.tests.common import TestEventExhibitorCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users


class TestSponsorData(TestEventExhibitorCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSponsorData, cls).setUpClass()

        cls.sponsor_0.write({
            'hour_from': 8.0,
            'hour_to': 18.0,
        })

        cls.wevent_exhib_dt = patch(
            'odoo.addons.website_event_exhibitor.models.event_sponsor.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.mock_wevent_exhib_dt = cls.wevent_exhib_dt.start()
        cls.mock_wevent_exhib_dt.now.return_value = cls.reference_now
        cls.addClassCleanup(cls.wevent_exhib_dt.stop)

    @users('user_eventmanager')
    def test_event_date_computation(self):
        """ Test date computation. Pay attention that mocks returns UTC values, meaning
        we have to take into account Europe/Brussels offset (+2 in July) """
        event = self.env['event.event'].browse(self.event_0.id)
        sponsor = self.env['event.sponsor'].browse(self.sponsor_0.id)
        event.invalidate_cache(fnames=['is_ongoing'])
        self.assertTrue(sponsor.is_in_opening_hours)
        self.assertTrue(event.is_ongoing)

        # After hour_from (9 > 8)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 7, 0, 0)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 7, 0, 0)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertTrue(sponsor.is_in_opening_hours)
        self.assertTrue(event.is_ongoing)

        # At hour_from (8 = 8)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 6, 0, 0)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 6, 0, 0)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertTrue(sponsor.is_in_opening_hours)
        self.assertTrue(event.is_ongoing)

        # Started but not opened (7h59 < 8)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 5, 59, 59)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 5, 59, 59)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)
        self.assertTrue(event.is_ongoing)

        # Evening event is not in opening hours (20 > 18)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 18, 0, 0)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 18, 0, 0)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)
        self.assertTrue(event.is_ongoing)

        # First day begins later
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 5, 6, 30, 0)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 5, 6, 30, 0)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)
        self.assertFalse(event.is_ongoing)

        # End day finished sooner
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 7, 13, 0, 1)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 7, 13, 0, 1)
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)
        self.assertFalse(event.is_ongoing)

        # Use "00:00" as opening hours for sponsor -> should still work
        event.invalidate_cache(fnames=['is_ongoing'])
        sponsor.hour_from = 0.0  # 0 -> 18

        # Inside opening hours (17 < 18)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 15, 0, 1)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 15, 0, 1)
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertTrue(sponsor.is_in_opening_hours)

        # Outside opening hours (21 > 18)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 19, 0, 1)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 19, 0, 1)
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)

        # Use "00:00" as closing hours for sponsor -> should still work
        # (considered 'at midnight the next day')
        sponsor.hour_from = 10.0
        sponsor.hour_to = 0.0

        # Inside opening hours (11 > 10)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 9, 0, 1)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 9, 0, 1)
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertTrue(sponsor.is_in_opening_hours)

        # Outside opening hours (7 < 10)
        self.mock_wevent_dt.now.return_value = datetime(2020, 7, 6, 5, 0, 1)
        self.mock_wevent_exhib_dt.now.return_value = datetime(2020, 7, 6, 5, 0, 1)
        sponsor.invalidate_cache(fnames=['is_in_opening_hours'])
        self.assertFalse(sponsor.is_in_opening_hours)
