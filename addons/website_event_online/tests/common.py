# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from unittest.mock import patch

from odoo.addons.event.tests.common import TestEventCommon
from odoo.fields import Datetime as FieldsDatetime, Date as FieldsDate
from odoo.tests.common import SavepointCase


class EventDtPatcher(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(EventDtPatcher, cls).setUpClass()

        cls.reference_now = datetime(2020, 7, 6, 10, 0, 0)
        cls.reference_today = datetime(2020, 7, 6)

        cls.event_dt = patch(
            'odoo.addons.event.models.event_event.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.wevent_main_dt = patch(
            'odoo.addons.website_event.controllers.main.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.event_online_dt = patch(
            'odoo.addons.website_event_online.models.event_event.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.event_date = patch(
            'odoo.addons.event.models.event_event.fields.Date',
            wraps=FieldsDate
        )
        cls.wevent_main_date = patch(
            'odoo.addons.website_event.controllers.main.fields.Date',
            wraps=FieldsDate
        )
        cls.mock_event_dt = cls.event_dt.start()
        cls.mock_wevent_main_dt = cls.wevent_main_dt.start()
        cls.mock_event_online_dt = cls.event_online_dt.start()
        cls.mock_event_date = cls.event_date.start()
        cls.mock_wevent_main_date = cls.wevent_main_date.start()
        cls.mock_event_dt.now.return_value = cls.reference_now
        cls.mock_wevent_main_dt.now.return_value = cls.reference_now
        cls.mock_event_online_dt.now.return_value = cls.reference_now
        cls.mock_event_date.today.return_value = cls.reference_today
        cls.mock_wevent_main_date.today.return_value = cls.reference_today
        cls.addClassCleanup(cls.event_dt.stop)
        cls.addClassCleanup(cls.wevent_main_dt.stop)
        cls.addClassCleanup(cls.event_online_dt.stop)
        cls.addClassCleanup(cls.event_date.stop)
        cls.addClassCleanup(cls.wevent_main_date.stop)


class TestEventOnlineCommon(TestEventCommon, EventDtPatcher):

    @classmethod
    def setUpClass(cls):
        super(TestEventOnlineCommon, cls).setUpClass()

        # event if 8-18 in Europe/Brussels (DST) (first day: begins at 9, last day: ends at 15)
        cls.event_0.write({
            'date_begin': datetime.combine(cls.reference_now, time(7, 0)) - timedelta(days=1),
            'date_end': datetime.combine(cls.reference_now, time(13, 0)) + timedelta(days=1),
        })
