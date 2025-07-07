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
        self.url_open(f'/event/{self.event_0.id}/registration/confirm', data={
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

    def test_website_event_questions(self):
        """ Will execute the tour that fills up two tickets with a few questions answers
        and then assert that the answers are correctly saved for each attendee. """

        self.design_fair_event = self.env['event.event'].create({
            'name': 'Design Fair New York',
            'date_begin': fields.Datetime.now() - relativedelta(days=15),
            'date_end': fields.Datetime.now() + relativedelta(days=15),
            'event_ticket_ids': [(0, 0, {
                'name': 'Free',
                'start_sale_datetime': fields.Datetime.now() - relativedelta(days=15)
            }), (0, 0, {
                'name': 'Other',
                'start_sale_datetime': fields.Datetime.now() - relativedelta(days=15)
            })],
            'website_published': True,
            'question_ids': [(0, 0, {
                'title': 'Name',
                'question_type': 'name',
            }), (0, 0, {
                'title': 'Email',
                'question_type': 'email',
            }), (0, 0, {
                'title': 'Phone',
                'question_type': 'phone',
            }), (0, 0, {
                'title': 'Company Name',
                'question_type': 'company_name',
            }), (0, 0, {
                'title': 'Meal Type',
                'question_type': 'simple_choice',
                'answer_ids': [
                    (0, 0, {'name': 'Mixed'}),
                    (0, 0, {'name': 'Vegetarian'}),
                    (0, 0, {'name': 'Pastafarian'})
                ]
            }), (0, 0, {
                'title': 'Allergies',
                'question_type': 'text_box'
            }), (0, 0, {
                'title': 'How did you learn about this event?',
                'question_type': 'simple_choice',
                'once_per_order': True,
                'answer_ids': [
                    (0, 0, {'name': 'Our website'}),
                    (0, 0, {'name': 'Commercials'}),
                    (0, 0, {'name': 'A friend'})
                ]
            })]
        })

        self.start_tour("/", 'test_tickets_questions', login="portal")

        registrations = self.env['event.registration'].search([
            ('email', 'in', ['attendee-a@gmail.com', 'attendee-b@gmail.com'])
        ])
        self.assertEqual(len(registrations), 2)
        first_registration = registrations.filtered(lambda reg: reg.email == 'attendee-a@gmail.com')
        second_registration = registrations.filtered(lambda reg: reg.email == 'attendee-b@gmail.com')
        self.assertEqual(first_registration.name, 'Attendee A')
        self.assertEqual(first_registration.phone, '+32499123456')
        self.assertEqual(second_registration.name, 'Attendee B')
        self.assertEqual(second_registration.company_name, 'My Company')

        event_questions = registrations.mapped('event_id.question_ids')
        self.assertEqual(len(event_questions), 7)

        first_registration_answers = first_registration.registration_answer_ids
        self.assertEqual(len(first_registration_answers), 6)

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Meal Type'
        ).value_answer_id.name, 'Vegetarian')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Allergies'
        ).value_text_box, 'Fish and Nuts')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'How did you learn about this event?'
        ).value_answer_id.name, 'A friend')

        second_registration_answers = second_registration.registration_answer_ids
        self.assertEqual(len(second_registration_answers), 5)

        self.assertEqual(second_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Meal Type'
        ).value_answer_id.name, 'Pastafarian')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'How did you learn about this event?'
        ).value_answer_id.name, 'A friend')

    def test_website_event_search(self):
        """ Ensure filters are not reset when changing pages or performing a search. """
        tag_category = self.env['event.tag.category'].create({'name': 'Test Category'})

        tags = self.env['event.tag'].create([
            {'name': 'tag 1', 'category_id': tag_category.id},
            {'name': 'tag 2', 'category_id': tag_category.id},
        ])

        # Need to create a bunch of events to have severals pages
        self.env['event.event'].create([
            {
                'name': f'Filter Test Event - {tag.name}',
                'website_published': True,
                'date_begin': datetime.today() - timedelta(days=1),
                'date_end': datetime.today() + timedelta(days=1),
                'tag_ids': tag,
            }
            for tag in tags
            for _ in range(20)
        ])

        self.start_tour('/event', 'test_website_event_search', login='admin')


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
        self.assertEqual(resp.status_code, 404, 'Public must not have access to unpublished event')

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
