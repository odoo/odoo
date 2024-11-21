# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.website.models.website_visitor import WebsiteVisitor
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.tests.common import users

class TestTrackData(TestEventOnlineCommon):

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
