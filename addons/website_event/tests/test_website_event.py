# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, http
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_event.tests.common import TestEventOnlineCommon, OnlineEventCase
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger
from odoo.tests.common import users

class TestEventRegisterUTM(HttpCase, TestEventOnlineCommon):
    def test_event_registration_utm_values(self):
        self.event_0.registration_ids.unlink()
        self.event_0.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                }),
            ],
            'is_published': True
        })
        event_campaign = self.env['utm.campaign'].create({'name': 'utm event test'})

        self.authenticate(None, None)
        self.opener.cookies.update({
            'odoo_utm_campaign': event_campaign.name,
            'odoo_utm_source': self.env.ref('utm.utm_source_newsletter').name,
            'odoo_utm_medium': self.env.ref('utm.utm_medium_email').name
        })
        event_questions = self.event_0.question_ids
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        self.assertTrue(name_question and email_question)
        # get 1 free ticket
        self.url_open(f'/event/{self.event_0.id}/registration/attendee-details/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            '1-event_ticket_id': self.event_0.event_ticket_ids[0].id,
            'csrf_token': http.Request.csrf_token(self),
        })
        new_registration = self.event_0.registration_ids
        self.assertEqual(len(new_registration), 1)
        self.assertEqual(new_registration.utm_campaign_id, event_campaign)
        self.assertEqual(new_registration.utm_source_id, self.env.ref('utm.utm_source_newsletter'))
        self.assertEqual(new_registration.utm_medium_id, self.env.ref('utm.utm_medium_email'))


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_website_event_tour_admin(self):
        self.upcoming_event = self.env['event.event'].create({
            'name': 'Upcoming Event',
            'date_begin': fields.Datetime.now() + relativedelta(days=10),
            'date_end': fields.Datetime.now() + relativedelta(days=13),
            'website_published': True,
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_event_tour', login='admin')

    def test_website_event_pages_seo(self):
        website = self.env['website'].get_current_website()
        event = self.env['event.event'].create({
            'name': 'Event With Menu',
            'website_menu': True,
            'website_id': website.id,
        })
        intro_event_menu = event.introduction_menu_ids
        url = intro_event_menu.menu_id._clean_url()
        self.start_tour(self.env['website'].get_client_action_url(url), 'website_event_pages_seo', login='admin')
        view_key = intro_event_menu.view_id.key
        specific_view = website.with_context(website_id=website.id).viewref(view_key)
        self.assertEqual(specific_view.website_meta_title, "Hello, world!")
        self.assertEqual(event.website_meta_title, False)

    def test_website_event_registrations(self):
        """ Check that registrations with and without tickets work from both the tickets form and
        the attendee details form. """
        date_begin = fields.Datetime.now() - relativedelta(days=15)
        date_end = fields.Datetime.now() + relativedelta(days=15)

        event_no_tickets_without_questions, event_no_tickets_with_questions, event_without_questions, event_with_questions = self.env['event.event'].create([{
            'name': 'Event No tickets And Without Questions',
            'date_begin': date_begin,
            'date_end': date_end,
            'website_published': True,
        }, {
            'name': 'Event No tickets And With Questions',
            'date_begin': date_begin,
            'date_end': date_end,
            'website_published': True,
        }, {
            'name': 'Event Without Questions',
            'date_begin': date_begin,
            'date_end': date_end,
            'website_published': True,
        }, {
            'name': 'Event With Questions',
            'date_begin': date_begin,
            'date_end': date_end,
            'website_published': True,
        }])
        # Remove default questions from events to test the registrations without attendee details.
        event_without_questions.question_ids.unlink()
        event_no_tickets_without_questions.question_ids.unlink()
        ticket_without_questions_1, ticket_without_questions_2, ticket_with_questions_1, ticket_with_questions_2 = self.env['event.event.ticket'].create([{
            'name': 'Regular',
            'event_id': event_without_questions.id,
            }, {
            'name': 'VIP',
            'event_id': event_without_questions.id,
        }, {
            'name': 'Regular',
            'event_id': event_with_questions.id,
            }, {
            'name': 'VIP',
            'event_id': event_with_questions.id,
        }])
        name_question, email_question, phone_question = event_with_questions.question_ids.filtered(
            lambda q: q.question_type in ('name', 'email', 'phone')
        )
        company_name_question, meal_type_question, allergies_question, learn_about_question = self.env['event.question'].create([{
            'title': 'Company Name',
            'question_type': 'company_name',
            'event_id': event_with_questions.id,
        }, {
            'title': 'Meal Type',
            'question_type': 'simple_choice',
            'event_id': event_with_questions.id,
            'answer_ids': [
                (0, 0, {'name': 'Mixed'}),
                (0, 0, {'name': 'Vegetarian'}),
                (0, 0, {'name': 'Pastafarian'})
            ]
        }, {
            'title': 'Allergies',
            'question_type': 'text_box',
            'event_id': event_with_questions.id,
        }, {
            'title': 'How did you learn about this event?',
            'question_type': 'simple_choice',
            'once_per_order': True,
            'event_id': event_with_questions.id,
            'answer_ids': [
                (0, 0, {'name': 'Our website'}),
                (0, 0, {'name': 'Commercials'}),
                (0, 0, {'name': 'A friend'})
            ]
        }])

        self.start_tour('/', 'website_event_registrations', login='portal')
        # Check that the registrations without tickets work form both tickets form or attendee details form.
        self.assertEqual(len(event_no_tickets_without_questions.registration_ids), 4)
        self.assertEqual(len(event_no_tickets_with_questions.registration_ids), 1)

        # Check that the registrations without questions have been recorded.
        self.assertEqual(len(ticket_without_questions_1.registration_ids), 3)
        self.assertEqual(len(ticket_without_questions_2.registration_ids), 2)

        registration_with_questions_1 = ticket_with_questions_1.registration_ids.filtered_domain([
            ('name', '=', 'Attendee A'),
            ('email', '=', 'attendee-a@gmail.com'),
            ('phone', '=', '+32499123456')
        ])
        registration_with_questions_2 = ticket_with_questions_2.registration_ids.filtered_domain([
            ('name', '=', 'Attendee B'),
            ('email', '=', 'attendee-b@gmail.com'),
            ('company_name', '=', 'My Company')
        ])
        # Check that the registrations with questions have been recorded.
        self.assertEqual(len(registration_with_questions_1), 1)
        self.assertEqual(len(registration_with_questions_2), 1)

        registration_with_questions_1_answer_ids_data = [
            (name_question.id, 'Attendee A', False),
            (email_question.id, 'attendee-a@gmail.com', False),
            (phone_question.id, '+32499123456', False),
            (meal_type_question.id, False, 'Vegetarian'),
            (allergies_question.id, 'Fish and Nuts', False),
            (learn_about_question.id, False, 'A friend')
        ]
        registration_with_questions_2_answer_ids_data = [
            (name_question.id, 'Attendee B', False),
            (email_question.id, 'attendee-b@gmail.com', False),
            (company_name_question.id, 'My Company', False),
            (meal_type_question.id, False, 'Pastafarian'),
            (learn_about_question.id, False, 'A friend')
        ]
        # Check that the attendee answers of the registration with questions have been recorded.
        self.assertCountEqual(
            registration_with_questions_1.registration_answer_ids.mapped(lambda ra: (ra.question_id.id, ra.value_text_box, ra.value_answer_id.name)),
            registration_with_questions_1_answer_ids_data
        )
        self.assertCountEqual(
            registration_with_questions_2.registration_answer_ids.mapped(lambda ra: (ra.question_id.id, ra.value_text_box, ra.value_answer_id.name)),
            registration_with_questions_2_answer_ids_data
        )


@tagged('post_install', '-at_install')
class TestWebsiteAccess(HttpCaseWithUserDemo, OnlineEventCase):

    def setUp(self):
        super(TestWebsiteAccess, self).setUp()

        self.website = self.env['website'].create({'name': 'Website Test'})
        self.partner = self.env['res.partner'].create([{
            'name': 'Test Partner1',
            'email': 'test@example.com',
            'city': 'Turlock',
            'state_id': self.env.ref('base.state_us_5').id,
            'country_id': self.env.ref('base.us').id,
        }])
        self.events = self.env['event.event'].create([{
            'name': 'Event 0 - Sitemap test',
            'website_published': True,
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
            'address_id': self.partner.id,
        }, {
            'name': 'Event 1 - Sitemap test',
            'website_published': True,
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        }, {
            'name': 'Event 2 - Sitemap test',
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        }])

        self.portal_user = mail_new_test_user(
            self.env, name='Smeagol', login='user_portal', password='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

    def test_website_access_event_manager(self):
        """ Event managers are allowed to access both published and unpublished events """
        self.authenticate('user_eventmanager', 'user_eventmanager')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Managers must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Managers must have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Managers must see the unpublished events.')
        self.assertTrue(unpublished_events[0].name in resp.text, 'Managers must see the published events.')

    def test_website_access_event_uer(self):
        """ Event users are allowed to access both published and unpublished events """
        self.authenticate('user_eventuser', 'user_eventuser')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Event user must see the unpublished events.')
        self.assertTrue(unpublished_events[0].name in resp.text, 'Event user must see the published events.')

    @mute_logger('odoo.http')
    def test_website_access_portal(self):
        """ Portal users access only published events """
        self.authenticate('user_portal', 'user_portal')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Portal user must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 403, 'Portal user must not have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Portal must see the published events.')
        self.assertFalse(unpublished_events[0].name in resp.text, 'Portal should not see the unpublished events.')

    @mute_logger('odoo.http')
    def test_website_access_public(self):
        """ Public users access only published events """
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Public must have access to published event')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 403, 'Public must not have access to unpublished event')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Public must see the published events.')
        self.assertFalse(unpublished_events[0].name in resp.text, 'Public should not see the unpublished events.')

    def test_sitemap(self):
        resp = self.url_open('/sitemap.xml')
        self.assertTrue('/event/event-0' in resp.text, 'Published events must be present in the sitemap')
        self.assertTrue('/event/event-1' in resp.text, 'Published events must be present in the sitemap')
        self.assertFalse('/event/event-2' in resp.text, 'Unpublished events must not be present in the sitemap')

    @users('user_portal')
    def test_check_search_in_address(self):
        ret = self.env['event.event']._search_get_detail(
            self.website, order=None, options={'displayDescription':'', 'displayDetail':''}
        )
        result = ret['search_extra'](self.env, 'Turlock')[0][-1].get_result_ids()
        self.assertEqual(*result, self.events[0].id, 'Event should exist for the searched term')

        with self.assertRaises(AccessError):
            self.env['res.partner'].browse(self.partner.id).read()
