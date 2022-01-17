# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo.addons.test_event_full.tests.common import TestEventFullCommon
from odoo.addons.website.tests.test_performance import UtilPerf
from odoo.tests.common import users, warmup, Form
from odoo.tests import tagged


@tagged('event_performance', 'post_install', '-at_install')
class EventPerformanceCase(TestEventFullCommon):

    def setUp(self):
        super(EventPerformanceCase, self).setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self._flush_tracking()

    def _flush_tracking(self):
        """ Force the creation of tracking values notably, and ensure tests are
        reproducible. """
        self.env['base'].flush()
        self.cr.flush()


@tagged('event_performance', 'post_install', '-at_install')
class TestEventPerformance(EventPerformanceCase):

    @users('event_user')
    @warmup
    def test_event_create_batch_notype(self):
        """ Test multiple event creation (import) """
        batch_size = 20

        # simple without type involved
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=440):  # tef only: 440 (434) - com runbot: 434 - ent runbot 440
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = [
                dict(self.event_base_vals,
                     website_menu=False)
                for x in range(batch_size)
            ]
            self.env['event.event'].create(event_values)

    @users('event_user')
    @warmup
    def test_event_create_batch_notype_website(self):
        """ Test multiple event creation (import) """
        batch_size = 20

        # simple without type involved + website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=5585):  # tef only: 5160 (5155) - com runbot: 5159 - ent runbot 5584
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = [
                dict(self.event_base_vals,
                     website_menu=True
                    )
                for x in range(batch_size)
            ]
            self.env['event.event'].create(event_values)

    @users('event_user')
    @warmup
    def test_event_create_batch_wtype(self):
        """ Test multiple event creation (import) """
        batch_size = 20
        event_type = self.env['event.type'].browse(self.test_event_type.ids)

        # complex with type
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=786):  # tef only: 785 (779) - com runbot: 779 - ent runbot 779
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = [
                dict(self.event_base_vals,
                     event_type_id=event_type.id,
                     website_menu=False,
                    )
                for x in range(batch_size)
            ]
            self.env['event.event'].create(event_values)

    @users('event_user')
    @warmup
    def test_event_create_batch_wtype_website(self):
        """ Test multiple event creation (import) """
        batch_size = 20
        event_type = self.env['event.type'].browse(self.test_event_type.ids)

        # complex with type + website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=5937):  # tef only: 5512 (5507) - com runbot: 5511 - ent runbot 5936
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = [
                dict(self.event_base_vals,
                     event_type_id=event_type.id,
                    )
                for x in range(batch_size)
            ]
            self.env['event.event'].create(event_values)


    @users('event_user')
    @warmup
    def test_event_create_form_notype(self):
        """ Test a single event creation using Form """
        has_social = 'social_menu' in self.env['event.event']  # otherwise view may crash in enterprise

        # no type, no website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=228):  # tef only: 178 - com runbot: 177
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.event']) as event_form:
                event_form.name = 'Test Event'
                event_form.date_begin = self.reference_now + timedelta(days=1)
                event_form.date_end = self.reference_now + timedelta(days=5)
                event_form.website_menu = False
                if has_social:
                    event_form.social_menu = False
            _event = event_form.save()

    @users('event_user')
    @warmup
    def test_event_create_form_notype_website(self):
        """ Test a single event creation using Form """
        has_social = 'social_menu' in self.env['event.event']  # otherwise view may crash in enterprise

        # no type, website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=736):  # tef only: 624 - com runbot: 624
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.event']) as event_form:
                event_form.name = 'Test Event'
                event_form.date_begin = self.reference_now + timedelta(days=1)
                event_form.date_end = self.reference_now + timedelta(days=5)
                event_form.website_menu = True
                if has_social:
                    event_form.social_menu = False
            _event = event_form.save()

    @users('event_user')
    @warmup
    def test_event_create_form_type_website(self):
        """ Test a single event creation using Form """
        event_type = self.env['event.type'].browse(self.test_event_type.ids)
        has_social = 'social_menu' in self.env['event.event']  # otherwise view may crash in enterprise

        # type and website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=784):  # tef only: 673 - com runbot: 675
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.event']) as event_form:
                event_form.name = 'Test Event'
                event_form.date_begin = self.reference_now + timedelta(days=1)
                event_form.date_end = self.reference_now + timedelta(days=5)
                event_form.event_type_id = event_type
                if has_social:
                    event_form.social_menu = False

    @users('event_user')
    @warmup
    def test_event_create_single_notype(self):
        """ Test a single event creation """
        # simple without type involved
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=41):  # tef only: 41 (35) - com runbot: 35
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = dict(
                self.event_base_vals,
                website_menu=False
            )
            self.env['event.event'].create([event_values])

    @users('event_user')
    @warmup
    def test_event_create_single_notype_website(self):
        """ Test a single event creation """
        # simple without type involved + website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=379):  # tef only: 353 (348) - com runbot: 352 - ent runbot 378
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = dict(
                self.event_base_vals,
                website_menu=True
            )
            self.env['event.event'].create([event_values])

    @users('event_user')
    @warmup
    def test_event_create_single_wtype(self):
        """ Test a single event creation """
        event_type = self.env['event.type'].browse(self.test_event_type.ids)

        # complex with type
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=82):  # tef only: 81 (75) - com runbot: 75 - ent runbot 75
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = dict(
                self.event_base_vals,
                event_type_id=event_type.id,
                website_menu=False
            )
            self.env['event.event'].create([event_values])

    @users('event_user')
    @warmup
    def test_event_create_single_wtype_website(self):
        """ Test a single event creation """
        event_type = self.env['event.type'].browse(self.test_event_type.ids)

        # complex with type + website
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=426):  # tef only: 400 (395) - com runbot: 399 - ent runbot 425
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            event_values = dict(
                self.event_base_vals,
                event_type_id=event_type.id,
            )
            self.env['event.event'].create([event_values])


@tagged('event_performance', 'registration_performance', 'post_install', '-at_install')
class TestRegistrationPerformance(EventPerformanceCase):

    @users('event_user')
    @warmup
    def test_registration_create_batch(self):
        """ Test multiple registrations creation (batch of 10 without partner
        and batch of 10 with partner)

        # TODO: with self.profile(collectors=['sql']) as _profile:
        """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=835):  # tef only: 789 - com runbot 832 - ent runbot 834
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = [
                dict(reg_data,
                     event_id=event.id)
                for reg_data in self.customer_data
            ]
            registration_values += [
                {'event_id': event.id,
                 'partner_id': partner.id,
                } for partner in self.partners
            ]
            _registrations = self.env['event.registration'].create(registration_values)

    @users('event_user')
    @warmup
    def test_registration_create_batch_nolead(self):
        """ Test multiple registrations creation (batch of 10 without partner
        and batch of 10 with partner)

        # TODO: with self.profile(collectors=['sql']) as _profile:
        """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=319):  # tef only: 276 - com runbot 315 - ent runbot 318
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = [
                dict(reg_data,
                     event_id=event.id)
                for reg_data in self.customer_data
            ]
            registration_values += [
                {'event_id': event.id,
                 'partner_id': partner.id,
                } for partner in self.partners
            ]
            _registrations = self.env['event.registration'].with_context(event_lead_rule_skip=True).create(registration_values)

    @users('event_user')
    @warmup
    def test_registration_create_batch_website(self):
        """ Test multiple registrations creation  (batch of 10 without partner
        and batch of 10 with partner) with some additional informations (register
        form like) """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=905):  # tef only: 859 - com runbot 902
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = [
                dict(reg_data,
                     event_id=event.id)
                for reg_data in self.website_customer_data
            ]
            registration_values += [
                {'event_id': event.id,
                 'partner_id': partner.id,
                 'registration_answer_ids': self.website_customer_data[0]['registration_answer_ids'],
                } for partner in self.partners
            ]
            _registrations = self.env['event.registration'].create(registration_values)

    @users('event_user')
    @warmup
    def test_registration_create_form_customer(self):
        """ Test a single registration creation using Form """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=231):  # tef only: 211 - com runbot 216
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.registration']) as reg_form:
                reg_form.event_id = event
                reg_form.email = 'email.00@test.example.com'
                reg_form.mobile = '0456999999'
                reg_form.name = 'My Customer'
                reg_form.phone = '0456000000'
            _registration = reg_form.save()

    @users('event_user')
    @warmup
    def test_registration_create_form_partner(self):
        """ Test a single registration creation using Form """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=234):  # tef only: 214 - com runbot 218
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.registration']) as reg_form:
                reg_form.event_id = event
                reg_form.partner_id = self.partners[0]
            _registration = reg_form.save()

    @users('event_user')
    @warmup
    def test_registration_create_form_partner_nolead(self):
        """ Test a single registration creation using Form """
        event = self.env['event.event'].browse(self.test_event.ids)

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=141):  # tef only: 123 - com runbot 124
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['event.registration'].with_context(event_lead_rule_skip=True)) as reg_form:
                reg_form.event_id = event
                reg_form.partner_id = self.partners[0]
            _registration = reg_form.save()

    @users('event_user')
    @warmup
    def test_registration_create_single_customer(self):
        """ Test a single registration creation """
        event = self.env['event.event'].browse(self.test_event.ids)

        # simple customer data
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=143):  # tef only: 136 - com runbot 141
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = dict(
                self.customer_data[0],
                event_id=event.id)
            _registration = self.env['event.registration'].create([registration_values])

    @users('event_user')
    @warmup
    def test_registration_create_single_partner(self):
        """ Test a single registration creation """
        event = self.env['event.event'].browse(self.test_event.ids)

        # partner-based customer
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=150):  # tef only: 144 - com runbot 149
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = {
                'event_id': event.id,
                'partner_id': self.partners[0].id,
            }
            _registration = self.env['event.registration'].create([registration_values])

    @users('event_user')
    @warmup
    def test_registration_create_single_partner_nolead(self):
        """ Test a single registration creation """
        event = self.env['event.event'].browse(self.test_event.ids)

        # partner-based customer
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=59):  # tef only: 55 - com runbot 57
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = {
                'event_id': event.id,
                'partner_id': self.partners[0].id,
            }
            _registration = self.env['event.registration'].with_context(event_lead_rule_skip=True).create([registration_values])

    @users('event_user')
    @warmup
    def test_registration_create_single_website(self):
        """ Test a single registration creation """
        event = self.env['event.event'].browse(self.test_event.ids)

        # website customer data
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=154):  # tef only: 145 - com runbot 150
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            registration_values = dict(
                self.website_customer_data[0],
                event_id=event.id)
            _registration = self.env['event.registration'].create([registration_values])


@tagged('event_performance', 'event_online', 'post_install', '-at_install')
class TestOnlineEventPerformance(EventPerformanceCase, UtilPerf):

    @classmethod
    def setUpClass(cls):
        super(TestOnlineEventPerformance, cls).setUpClass()
        # if website_livechat is installed, disable it
        if 'channel_id' in cls.env['website']:
            cls.env['website'].search([]).channel_id = False

        cash_journal = cls.env['account.journal'].create({
            'name': 'Cash - Test',
            'type': 'cash',
            'code': 'CASH - Test'
        })
        cls.env['payment.acquirer'].search([('provider', '=', 'test')]).write({
            'journal_id': cash_journal.id,
            'state': 'test'
        })

        # clean even page to make it reproducible
        cls.env['event.event'].search([('name', '!=', 'Test Event')]).write({'active': False})
        # create noise for events
        cls.noise_events = cls.env['event.event'].create([
            {'name': 'Event %02d' % idx,
             'date_begin': cls.reference_now + timedelta(days=(-2 + int(idx/10))),
             'date_end': cls.reference_now + timedelta(days=5),
             'is_published': True,
            }
            for idx in range(0, 50)
        ])

    def _test_url_open(self, url):
        url += ('?' not in url and '?' or '') + '&nocache'
        return self.url_open(url)

    @warmup
    def test_event_page_event_manager(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate('user_eventmanager', 'user_eventmanager')
            with self.assertQueryCount(default=65):  # tef only: 64 (+1 ent)
                self._test_url_open('/event/%i' % self.test_event.id)

    @warmup
    def test_event_page_public(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=43):  # tef only: 43
                self._test_url_open('/event/%i' % self.test_event.id)

    @warmup
    def test_events_browse_event_manager(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate('user_eventmanager', 'user_eventmanager')
            with self.assertQueryCount(default=51):  # tef only: 50 (+1 ent)
                self._test_url_open('/event')

    @warmup
    def test_events_browse_public(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=32):  # tef only: 32
                self._test_url_open('/event')

    # @warmup
    # def test_register_public(self):
    #     with freeze_time(self.reference_now + timedelta(hours=3)):  # be sure sales has started
    #         self.assertTrue(self.test_event.event_registrations_started)
    #         self.authenticate(None, None)
    #         with self.assertQueryCount(default=99999):  # tef only: 1110
    #             self.browser_js(
    #                 '/event/%i/register' % self.test_event.id,
    #                 'odoo.__DEBUG__.services["web_tour.tour"].run("wevent_performance_register")',
    #                 'odoo.__DEBUG__.services["web_tour.tour"].tours.wevent_performance_register.ready',
    #                 login=None,
    #                 timeout=200,
    #             )

    #     # minimal checkup, to be improved in future tests independently from performance
    #     self.assertEqual(len(self.test_event.registration_ids), 3)
    #     self.assertEqual(len(self.test_event.registration_ids.visitor_id), 1)
