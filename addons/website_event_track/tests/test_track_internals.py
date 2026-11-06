# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< c7a3d32c3097900f63dd46253c5d0f36e87529a7
from datetime import datetime, timedelta
from freezegun import freeze_time
||||||| 555e93d608d4c9ef841f57280f5cc4a3907fae7d
from datetime import datetime, timedelta
=======
from datetime import date, datetime, timedelta
>>>>>>> 5f3f85dea8a416f80903455fb1aaa4799b673dfa
from unittest.mock import patch

from odoo import fields
from odoo.addons.website.models.website_visitor import WebsiteVisitor
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
<<<<<<< c7a3d32c3097900f63dd46253c5d0f36e87529a7
from odoo.tests.common import tagged, users
||||||| 555e93d608d4c9ef841f57280f5cc4a3907fae7d
from odoo.tests.common import users
=======
from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.tests.common import users
>>>>>>> 5f3f85dea8a416f80903455fb1aaa4799b673dfa


@tagged('event_track_internals')
class TestTrackData(TestEventOnlineCommon):

    @users('user_eventmanager')
    def test_track_duration(self):
        """ Test updating duration / end date """
        event = self.event_0.with_env(self.env)
        customer = self.event_customer.with_env(self.env)

        now = datetime(2025, 3, 5, 14, 0, 0)
        with freeze_time(now):
            tracks = self.env['event.track'].create([
                {
                    'date': now,
                    'duration': 4.5,
                    'event_id': event.id,
                    'name': 'Date + duration',
                    'partner_id': customer.id,
                }, {
                    'date': now,
                    'date_end': now + timedelta(hours=6, minutes=15),
                    'event_id': event.id,
                    'name': 'Date + end',
                    'partner_id': customer.id,
                }, {
                    'date': now,
                    'duration': False,
                    'event_id': event.id,
                    'name': 'Start only (duration False)',
                    'partner_id': customer.id,
                }, {
                    'date': now,
                    'event_id': event.id,
                    'name': 'Start only (default duration)',
                    'partner_id': customer.id,
                }, {
                    'duration': 3.75,
                    'event_id': event.id,
                    'name': 'Duration only',
                    'partner_id': customer.id,
                }, {
                    'duration': False,
                    'date_end': now,
                    'event_id': event.id,
                    'name': 'End only (duration False)',
                    'partner_id': customer.id,
                }, {
                    'duration': 2.5,
                    'date_end': now,
                    'event_id': event.id,
                    'name': 'End + duration',
                    'partner_id': customer.id,
                }, {
                    'date': now,
                    'date_end': now + timedelta(hours=6, minutes=15),
                    'duration': 10,
                    'event_id': event.id,
                    'name': 'Date + end + duration (such schrizo)',
                    'partner_id': customer.id,
                },
            ])

        for track, (exp_date, exp_date_end, exp_duration) in zip(tracks, [
            (now, now + timedelta(hours=4, minutes=30), 4.5),
            (now, now + timedelta(hours=6, minutes=15), 6.25),
            (now, now, 0),  # duration False = 0 = end = start
            (now, now + timedelta(minutes=30), 0.5),  # default duration is 0.5
            (False, False, 3.75),
            (now, now, 0),  # duration False = 0 = end = start
            (now - timedelta(hours=2, minutes=30), now, 2.5),
            (now, now + timedelta(hours=6, minutes=15), 6.25),
        ], strict=True):
            with self.subTest(track_name=track.name):
                self.assertEqual(track.date, exp_date)
                self.assertEqual(track.date_end, exp_date_end)
                self.assertEqual(track.duration, exp_duration)

        # update duration to check start / end update
        tracks[0].duration = 12
        self.assertEqual(tracks[0].date, now)
        self.assertEqual(tracks[0].date_end, now + timedelta(hours=12))
        self.assertEqual(tracks[0].duration, 12)

    @users('user_eventmanager')
    def test_track_partner_sync(self):
        """ Test registration computed fields about partner """
        test_email = '"Nibbler In Space" <nibbler@futurama.example.com>'
        test_phone = '0456001122'
        test_bio = '<p>UserInput</p>'
        # test_bio_void = '<p><br/></p>'

        event = self.env['event.event'].browse(self.event_0.ids)
        customer = self.env['res.partner'].browse(self.event_customer.id)

        # take all from partner
        new_track = self.env['event.track'].create({
            'event_id': event.id,
            'name': 'Mega Track',
            'partner_id': customer.id,
        })
        self.assertEqual(new_track.partner_id, customer)
        self.assertEqual(new_track.partner_name, customer.name)
        self.assertEqual(new_track.partner_email, customer.email)
        self.assertEqual(new_track.partner_phone, customer.phone)
        self.assertEqual(new_track.partner_biography, customer.website_description)
        self.assertIn(customer.name, new_track.partner_biography, 'Low-level test: ensure correctly updated')

        # partial update
        new_track = self.env['event.track'].create({
            'event_id': event.id,
            'name': 'Mega Track',
            'partner_id': customer.id,
            'partner_name': 'Nibbler In Space',
            'partner_email': test_email,
        })
        self.assertEqual(new_track.partner_id, customer)
        self.assertEqual(
            new_track.partner_name, 'Nibbler In Space',
            'Track should take user input over computed partner value')
        self.assertEqual(
            new_track.partner_email, test_email,
            'Track should take user input over computed partner value')
        self.assertEqual(
            new_track.partner_phone, customer.phone,
            'Track should take partner value if not user input')

        # already filled information should not be updated
        new_track = self.env['event.track'].create({
            'event_id': event.id,
            'name': 'Mega Track',
            'partner_name': 'Nibbler In Space',
            'partner_phone': test_phone,
            'partner_biography': test_bio,
        })
        self.assertEqual(new_track.partner_name, 'Nibbler In Space')
        self.assertEqual(new_track.partner_email, False)
        self.assertEqual(new_track.partner_phone, test_phone)
        self.assertEqual(new_track.partner_biography, test_bio)
        new_track.write({'partner_id': customer.id})
        self.assertEqual(new_track.partner_id, customer)
        self.assertEqual(
            new_track.partner_name, 'Nibbler In Space',
            'Track customer should not take over existing value')
        self.assertEqual(
            new_track.partner_email, customer.email,
            'Track customer should take over empty value')
        self.assertEqual(
            new_track.partner_phone, test_phone,
            'Track customer should not take over existing value')

        # contacts fields should be updated with track customer
        new_track = self.env['event.track'].create({
            'event_id': event.id,
            'name': 'Mega Track',
            'contact_phone': test_phone,
        })
        self.assertEqual(new_track.contact_email, False)
        self.assertEqual(new_track.contact_phone, test_phone)
        new_track.write({'partner_id': customer.id})
        self.assertEqual(new_track.partner_id, customer)
        self.assertEqual(
            new_track.contact_email, customer.email,
            'Track customer should take over empty contact email value')
        self.assertEqual(
            new_track.contact_phone, customer.phone,
            'Track customer should take over existing contact phone value')

    def test_split_track_by_days_long_duration(self):
        """ A track running over several days is split into one entry per day,
        and keeps its real duration across a daylight saving time change. """
        for date_tz, track_date, duration, expected_slots, end_hour in [
            # DST ends on 25 October 2026 at 03:00, the day lasts 25 hours
            ('Europe/Brussels', datetime(2026, 10, 24, 20, 0, 0), 50.0, {
                date(2026, 10, 24): [(22, 8)],
                date(2026, 10, 25): [(0, 100)],
                date(2026, 10, 26): [(0, 92)],
            }, 23),
            # DST starts on 30 April 2027 at midnight, the day starts at 01:00 and lasts 23 hours
            ('Africa/Cairo', datetime(2027, 4, 29, 20, 0, 0), 30.0, {
                date(2027, 4, 29): [(22, 8)],
                date(2027, 4, 30): [(1, 92)],
                date(2027, 5, 1): [(0, 20)],
            }, 5),
        ]:
            with self.subTest(date_tz=date_tz):
                self.event_0.track_ids.unlink()
                self.event_0.date_tz = date_tz
                track = self.env['event.track'].create({
                    'name': 'Marathon Track',
                    'event_id': self.event_0.id,
                    'date': track_date,
                    'duration': duration,
                    'is_published': True,
                })

                with MockRequest(self.env):
                    calendar_values = EventTrackController()._prepare_calendar_values(self.event_0)
                self.assertEqual(
                    {
                        day: [
                            (time_slot.hour, tracks_by_location[track.location_id][track]['rowspan'])
                            for time_slot, tracks_by_location in time_slots.items()
                            if track in tracks_by_location.get(track.location_id, {})
                        ]
                        for day, time_slots in calendar_values['time_slots'].items()
                    },
                    expected_slots,
                    'Each day of the agenda should only show the part of the track running on that day')
                last_time_slot = list(calendar_values['time_slots'][max(expected_slots)])[-1]
                self.assertEqual(last_time_slot.hour, end_hour, 'The agenda should end at the real end of the track')

class TestTrackSuggestions(TestEventOnlineCommon):

    def test_track_suggestion(self):
        [location_1, location_2] = self.env['event.track.location'].create([
            {'name': 'Location 1'},
            {'name': 'Location 2'},
        ])

        [tag_1, tag_2, tag_3, tag_4] = self.env['event.track.tag'].create([
            {'name': 'Tag 1'}, {'name': 'Tag 2'}, {'name': 'Tag 3'}, {'name': 'Tag 4'}
        ])

        date = fields.Datetime.from_string(datetime.now().strftime('%Y-%m-%d %H:00:00'))
        [track_1, track_2, track_3, track_4, track_5, track_6] = self.env['event.track'].create([{
            'name': 'Track 1',
            'location_id': location_1.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_2.id)],
            'date': date + timedelta(hours=-1),
        }, {
            'name': 'Track 2',
            'location_id': location_2.id,
            'event_id': self.event_0.id,
            'date': date,
        }, {
            'name': 'Track 3',
            'location_id': location_2.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id), (4, tag_4.id)],
            'date': date,
        }, {
            'name': 'Track 4',
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_2.id)],
            'date': date,
        }, {
            'name': 'Track 5',
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id)],
            'wishlisted_by_default': True,
            'date': date,
        }, {
            'name': 'Track 6',
            'location_id': location_1.id,
            'event_id': self.event_0.id,
            'tag_ids': [(4, tag_1.id), (4, tag_3.id)],
            'date': date,
        }])

        emp_visitor = self.env['website.visitor'].create({
            'partner_id': self.user_employee.partner_id.id,
            'access_token': self.user_employee.partner_id.id,
        })
        visitor_track = self.env['event.track.visitor'].create({
            'visitor_id': emp_visitor.id,
            'track_id': track_3.id,
            'is_wishlisted': True,
        })

        with patch.object(WebsiteVisitor, '_get_visitor_from_request', lambda *args, **kwargs: emp_visitor), \
                self.with_user('user_employee'):
            current_track = self.env['event.track'].browse(track_1.id)
            all_suggestions = current_track._get_track_suggestions()
            self.assertEqual(
                all_suggestions.ids,
                (track_3 + track_5 + track_4 + track_6 + track_2).ids # whlst / wishlst def / tags count / location
            )

            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertEqual(track_suggestion, track_3,
                'Returned track should be the manually wishlisted one')

            # remove wishlist, keynote should be top
            visitor_track.unlink()
            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertEqual(
                track_suggestion, track_5,
                'Returned track should be the default wishlisted one')

            # toggle wishlisted by default off through blacklist
            track_5_visitor = self.env['event.track.visitor'].sudo().create({
                'visitor_id': emp_visitor.id,
                'track_id': track_5.id,
                'is_blacklisted': True,
            })
            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertEqual(
                track_suggestion, track_4,
                'Returned track should the one with the most common tags as keynote is blacklisted')
            track_5_visitor.unlink()

            # remove keynote default, now based on tags
            track_5.write({'wishlisted_by_default': False})
            # all_suggestions.invalidate_model(['is_reminder_on'])
            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertEqual(
                track_suggestion, track_4,
                'Returned track should the one with the most common tags')

            # remove tags, now based on location
            all_suggestions.sudo().write({'tag_ids': [(5,)]})
            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertEqual(
                track_suggestion, track_6,
                'Returned track should the one with matching location')

            # remove location, now based o random
            all_suggestions.sudo().write({'location_id': False})
            track_suggestion = current_track._get_track_suggestions(limit=1)
            self.assertTrue(
                track_suggestion in [track_2, track_3, track_4, track_5, track_6],
                "Returned track should the a random one (but not the one we're trying to get suggestion for)")
