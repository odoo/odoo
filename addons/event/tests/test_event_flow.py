# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.event.tests.common import EventCase
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged("event_mail")
class TestEventFlow(EventCase):

    @users('user_eventmanager')
    def test_event_default_datetime(self):
        """ Check that the default date_begin and date_end are correctly set """

        # Should apply default datetimes
        with freeze_time(self.reference_now):
            default_event = self.env['event.event'].create({
                'name': 'Test Default Event',
            })
        self.assertEqual(default_event.date_begin, datetime.datetime.strptime('2022-09-05 15:30:00', '%Y-%m-%d %H:%M:%S'))
        self.assertEqual(default_event.date_end, datetime.datetime.strptime('2022-09-06 15:30:00', '%Y-%m-%d %H:%M:%S'))

        specific_datetimes = {
            'date_begin': self.reference_now + relativedelta(days=1),
            'date_end': self.reference_now + relativedelta(days=3),
        }

        # Should not apply default datetimes if values are set manually
        with freeze_time(self.reference_now):
            event = self.env['event.event'].create({
                'name': 'Test Event',
                **specific_datetimes,
            })
        self.assertEqual(event.date_begin, specific_datetimes['date_begin'])
        self.assertEqual(event.date_end, specific_datetimes['date_end'])

    @mute_logger('odoo.addons.event.models.event_mail')
    def test_event_missed_mail_template(self):
        """ Check that error on mail sending is ignored if corresponding mail template was deleted """
        test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
            'name': 'TestEvent',
            'date_begin': datetime.datetime.now() + relativedelta(days=-1),
            'date_end': datetime.datetime.now() + relativedelta(days=1),
            'seats_max': 2,
            'seats_limited': True,
        })

        scheduler = self.env['event.mail'].sudo().search([
            ('event_id', '=', test_event.id),
            ('interval_type', '=', 'after_sub')
        ])

        # Imagine user deletes mail template for whatever reason
        scheduler.template_ref.unlink()

        # EventUser create registrations for this event
        self.env['event.registration'].with_user(self.user_eventuser).create({
            'name': 'TestReg1',
            'event_id': test_event.id,
        })

        # Mails should not be sent
        self.assertFalse(scheduler.mail_registration_ids.mail_sent)
