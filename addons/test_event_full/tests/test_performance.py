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
        self.env.flush_all()
        self.cr.flush()


@tagged('event_performance', 'post_install', '-at_install')
class TestEventPerformance(EventPerformanceCase):

    @users('event_user')
    @warmup
    def test_event_create_batch_notype(self):
        """ Test multiple event creation (import) """
        batch_size = 20

        # simple without type involved
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=341):  # 335 (sometimes +6)
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=5368):  # com runbot: 4943 - +1 tef - ent runbot 5368
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=445):  # 439 (sometimes +6)
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=5480):  # com runbot: 5055 - +1 tef - ent runbot 5480
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=206):  # com runbot: 160
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            # Require for `website_menu` to be visible
            # <div name="event_menu_configuration" groups="base.group_no_one">
            with self.debug_mode():
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=667):  # com runbot: 566 - -1 tef - ent runbot: 666
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            # Require for `website_menu` to be visible
            # <div name="event_menu_configuration" groups="base.group_no_one">
            with self.debug_mode():
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=693):  # tef only: 593 - com runbot: 596 - ent runbot: 692
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            # Require for `website_menu` to be visible
            # <div name="event_menu_configuration" groups="base.group_no_one">
            with self.debug_mode():
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=37):  # 31 (sometimes +6)
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=352):  # com runbot: 326 - +1 tef - ent runbot 352
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=64):  # 58 (sometimes +6)
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=387):  # com runbot: 361 - +1 tef - ent runbot 387
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=686):  # tef only: 639 - com runbot 681
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=211):  # tef only: 168 - com runbot 207
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=697):  # tef only: 650 - com runbot 692
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=202):  # tef only: 184 - com runbot: 189
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=209):  # tef only: 188 - com runbot: 193
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

        with freeze_time(self.reference_now), self.assertQueryCount(event_user=124):  # tef only: 120? - com runbot 108 - ent runbot 122
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=125):  # tef only: 106 - com runbot: 122
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=129):  # tef only: 118 - com runbot: 125
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=46):  # tef only: 40 - com runbot: 42
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
        with freeze_time(self.reference_now), self.assertQueryCount(event_user=135):  # tef only: 124 - com runbot: 128
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
        url += ('?' not in url and '?' or '') + '&debug=disable-t-cache'
        return self.url_open(url)

    @warmup
    def test_event_page_event_manager(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate('user_eventmanager', 'user_eventmanager')
            with self.assertQueryCount(default=36):
                self._test_url_open('/event/%i' % self.test_event.id)

    @warmup
    def test_event_page_public(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=27):
                self._test_url_open('/event/%i' % self.test_event.id)

    @warmup
    def test_events_browse_event_manager(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate('user_eventmanager', 'user_eventmanager')
            with self.assertQueryCount(default=39):
                self._test_url_open('/event')

    @warmup
    def test_events_browse_public(self):
        # website customer data
        with freeze_time(self.reference_now):
            self.authenticate(None, None)
            with self.assertQueryCount(default=28):
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
