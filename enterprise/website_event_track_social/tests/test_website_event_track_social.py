# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from werkzeug.urls import url_join


class TestTrackPush(TestEventOnlineCommon):

    @classmethod
    def setUpClass(cls):
        super(TestTrackPush, cls).setUpClass()
        cls.website = cls.env['website'].create({'name': 'Website'})
        cls.event_0.write({'website_id': cls.website.id})

    def test_regular_track(self):
        """ Check that push reminders are sent to attendees that have wishlisted the track. """
        [track_1, track_2] = self.env['event.track'].create([{
            'name': 'Track 1',
            'event_id': self.event_0.id,
            'date': fields.Datetime.now() + relativedelta(hours=2),
        }, {
            'name': 'Track 2',
            'event_id': self.event_0.id,
            'date': fields.Datetime.now() + relativedelta(hours=2),
        }])

        visitors_track_1 = self.env['website.visitor'].create([{
            'name': 'Wishlisting Visitor 1',
            'access_token': 'f9d268880b2afc54313fa45b7871d336',
            'event_track_visitor_ids': [(0, 0, {
                'is_wishlisted': True,
                'track_id': track_1.id
            })],
            'push_subscription_ids': [(0, 0, {'push_token': 'AAAAAA'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }, {
            'name': 'Wishlisting Visitor 2',
            'access_token': 'f9d2d2bc34433e5477f6aa2772cca6b7',
            'event_track_visitor_ids': [(0, 0, {
                'is_wishlisted': True,
                'track_id': track_1.id
            })],
            'push_subscription_ids': [(0, 0, {'push_token': 'BBBBBB'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }])

        self.env['website.visitor'].create({
            'name': 'Wishlisting Visitor 3',
            'access_token': 'f9d2f351b2e4c32e9da07c8e6e2c26f3',
            'event_track_visitor_ids': [(0, 0, {
                'is_wishlisted': True,
                'track_id': track_2.id
            })],
            'push_subscription_ids': [(0, 0, {'push_token': 'CCCCCC'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        })

        track_1.write({
            'push_reminder': True,
            'push_reminder_delay': 10
        })
        track_1.flush_recordset(['push_reminder'])
        track_2.write({'push_reminder': True})
        track_2.flush_recordset(['push_reminder'])

        push_reminder = self.env['social.post'].search([('event_track_id', '=', track_1.id)])
        self.assertTrue(bool(push_reminder))
        self.assertEqual("Your favorite track 'Track 1' will start in 10 minutes!", push_reminder.message)
        self.assertEqual(
            url_join(track_1.event_id.get_base_url(), track_1.website_url),
            push_reminder.push_notification_target_url)
        self.assertEqual('scheduled', push_reminder.post_method)
        self.assertEqual(False, push_reminder.use_visitor_timezone)
        self.assertEqual(track_1.date - relativedelta(minutes=10), push_reminder.scheduled_date)

        targeted_visitors = self.env['website.visitor'].search(literal_eval(push_reminder.visitor_domain))
        self.assertEqual(targeted_visitors, visitors_track_1)

        track_1.write({
            'name': 'New Name',
            'push_reminder_delay': 20,
            'date': fields.Datetime.now() + relativedelta(hours=3)
        })
        track_1.flush_recordset(['name', 'date'])
        push_reminder = self.env['social.post'].search([('event_track_id', '=', track_1.id)])
        self.assertEqual("Your favorite track 'New Name' will start in 20 minutes!", push_reminder.message)
        self.assertEqual(track_1.date - relativedelta(minutes=20), push_reminder.scheduled_date)

        track_1.write({'push_reminder': False})
        track_1.flush_recordset(['push_reminder'])
        push_reminder = self.env['social.post'].search([('event_track_id', '=', track_1.id)])
        self.assertFalse(bool(push_reminder))

    def test_default_wishlisted(self):
        """ Check that push reminders are sent to attendees that have not blacklisted the track. """
        track_1 = self.env['event.track'].create([{
            'name': 'Track 1',
            'wishlisted_by_default': True,
            'event_id': self.event_0.id,
            'date': fields.Datetime.now() + relativedelta(hours=2),
        }])

        visitors = self.env['website.visitor'].create([{
            'name': 'Regular Visitor 1',
            'access_token': 'f9d2ee58283634915fa60795172ffcc2',
            'push_subscription_ids': [(0, 0, {'push_token': 'AAAAAA'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }, {
            'name': 'Regular Visitor 2',
            'access_token': 'f9d2c399f328eab40f3b65cf018b2bea',
            'push_subscription_ids': [(0, 0, {'push_token': 'BBBBBB'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        }])

        self.env['website.visitor'].create({
            'access_token': 'f9d29d32bd910e02391fe16d2ac50210',
            'name': 'Visitor Blacklist',
            'event_track_visitor_ids': [(0, 0, {
                'is_blacklisted': True,
                'track_id': track_1.id
            })],
            'push_subscription_ids': [(0, 0, {'push_token': 'CCCCCC'})],
            'event_registration_ids': [(0, 0, {
                'event_id': self.event_0.id
            })]
        })

        track_1.write({'push_reminder': True})
        track_1.flush_recordset(['push_reminder'])

        push_reminder = self.env['social.post'].search([('event_track_id', '=', track_1.id)])
        self.assertTrue(bool(push_reminder))
        targeted_visitors = self.env['website.visitor'].search(literal_eval(push_reminder.visitor_domain))
        self.assertEqual(visitors, targeted_visitors)
