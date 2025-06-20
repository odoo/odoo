# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from markupsafe import Markup
from requests import Session, PreparedRequest, Response

import datetime
import werkzeug

from odoo import tools
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


class TestMailingControllersCommon(MassMailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailingControllersCommon, cls).setUpClass()

        # cleanup lists
        cls.env['mailing.list'].search([]).unlink()

        cls._create_mailing_list()
        cls.test_mailing_on_contacts = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/><br />Go to <a id="url" href="https://www.example.com/foo/bar?baz=qux">this link</a></p>',
            'mailing_domain': [],
            'mailing_model_id': cls.env['ir.model']._get_id('mailing.contact'),
            'mailing_type': 'mail',
            'name': 'TestMailing on Contacts',
            'subject': 'TestMailing on Contacts',
        })
        cls.test_mailing_on_documents = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/><br />Go to <a id="url" href="https://www.example.com/foo/bar?baz=qux">this link</a></p>',
            'mailing_domain': [],
            'mailing_model_id': cls.env['ir.model']._get_id('res.partner'),
            'mailing_type': 'mail',
            'name': 'TestMailing on Documents',
            'subject': 'TestMailing on Documents',
        })
        cls.test_mailing_on_lists = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/><br />Go to <a id="url" href="https://www.example.com/foo/bar?baz=qux">this link</a></p>',
            'contact_list_ids': [(4, cls.mailing_list_1.id), (4, cls.mailing_list_2.id)],
            'mailing_model_id': cls.env['ir.model']._get_id('mailing.list'),
            'mailing_type': 'mail',
            'name': 'TestMailing on Lists',
            'reply_to': cls.email_reply_to,
            'subject': 'TestMailing on Lists',
        })

        cls.test_contact = cls.mailing_list_1.contact_ids[0]

        # freeze time base value
        cls._reference_now = datetime.datetime(2022, 6, 14, 10, 0, 0)

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        if r.url.startswith('https://www.example.com/foo/bar'):
            r = Response()
            r.status_code = 200
            return r
        return super()._request_handler(s, r, **kw)


@tagged('mailing_portal', 'post_install', '-at_install')
class TestMailingControllers(TestMailingControllersCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_email = tools.formataddr(('Déboulonneur', '<fleurus@example.com>'))
        cls.test_email_normalized = 'fleurus@example.com'

    def test_assert_initial_values(self):
        """ Ensure test base data to ease test understanding. Globally test_email
        is member of 2 mailing public lists. """
        memberships = self.env['mailing.subscription'].search([
            ('contact_id.email_normalized', '=', self.test_email_normalized)]
        )
        self.assertEqual(memberships.list_id, self.mailing_list_1 + self.mailing_list_3)
        self.assertEqual(memberships.mapped('opt_out'), [False, True])

        contact_l1 = self.mailing_list_1.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        self.assertTrue(contact_l1)
        self.assertFalse(contact_l1.is_blacklisted)
        self.assertFalse(contact_l1.message_ids)
        subscription_l1 = self.mailing_list_1.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l1
        )
        self.assertTrue(subscription_l1)
        self.assertFalse(subscription_l1.is_blacklisted)
        self.assertFalse(subscription_l1.opt_out)
        self.assertFalse(subscription_l1.opt_out_datetime)

        contact_l2 = self.mailing_list_2.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        self.assertFalse(contact_l2)

        contact_l3 = self.mailing_list_3.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        self.assertTrue(contact_l3)
        self.assertTrue(contact_l3 != contact_l1)
        self.assertFalse(contact_l3.is_blacklisted)
        subscription_l3 = self.mailing_list_3.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l3
        )
        self.assertFalse(subscription_l3.is_blacklisted)
        self.assertTrue(subscription_l3.opt_out)

        contact_l4 = self.mailing_list_4.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        self.assertFalse(contact_l4)

        self.assertFalse(self.env['mail.blacklist'].search([('email', '=', self.test_email_normalized)]))

    @mute_logger('odoo.http', 'odoo.addons.website.models.ir_ui_view')
    def test_mailing_report_unsubscribe(self):
        """ Test deactivation of mailing report sending. It requires usage of
        a hash token. """
        test_mailing = self.test_mailing_on_lists.with_env(self.env)
        self.env['ir.config_parameter'].sudo().set_param(
            'mass_mailing.mass_mailing_reports', True
        )
        hash_token = test_mailing._generate_mailing_report_token(self.user_marketing.id)
        self.authenticate('user_marketing', 'user_marketing')

        # TEST: various invalid cases
        for test_user_id, test_token, error_code in [
            (self.user_marketing.id, '', 400),  # no token
            (self.user_marketing.id, 'zboobs', 418),  # invalid token
            (self.env.uid, hash_token, 418),  # invalid credentials
        ]:
            with self.subTest(test_user_id=test_user_id, test_token=test_token):
                res = self.url_open(
                    werkzeug.urls.url_join(
                        test_mailing.get_base_url(),
                        f'mailing/report/unsubscribe?user_id={test_user_id}&token={test_token}',
                    )
                )
                self.assertEqual(res.status_code, error_code)
                self.assertTrue(self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mass_mailing_reports'))

        # TEST: not mailing user
        self.user_marketing.write({
            'groups_id': [(3, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        res = self.url_open(
            werkzeug.urls.url_join(
                test_mailing.get_base_url(),
                f'mailing/report/unsubscribe?user_id={self.user_marketing.id}&token={hash_token}',
            )
        )
        self.assertEqual(res.status_code, 418)
        self.assertTrue(self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mass_mailing_reports'))

        # TEST: finally valid call
        self.user_marketing.write({
            'groups_id': [(4, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        res = self.url_open(
            werkzeug.urls.url_join(
                test_mailing.get_base_url(),
                f'mailing/report/unsubscribe?user_id={self.user_marketing.id}&token={hash_token}',
            )
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mass_mailing_reports'))

    def test_mailing_unsubscribe_from_document_tour(self):
        """ Test portal unsubscribe on mailings performed on documents (not
        mailing lists or contacts). Primary effect is to automatically exclude
        the email (see tour).

        Two tests are performed (with and without existing list subscriptions)
        as it triggers the display of the mailing list part of the UI.

        Tour effects
          * unsubscribe from mailing based on a document = blocklist;
          * add feedback (block list): Other reason, with 'My feedback' feedback;
          * remove email from exclusion list;
          * re-add email to exclusion list;
        """
        opt_out_reasons = self.env['mailing.subscription.optout'].search([])
        test_mailing = self.test_mailing_on_documents.with_env(self.env)
        test_feedback = "My feedback"

        for test_email, tour_name in [
            ('"Not Déboulonneur" <not.fleurus@example.com>', 'mailing_portal_unsubscribe_from_document'),
            (self.test_email, 'mailing_portal_unsubscribe_from_document_with_lists'),
        ]:
            with self.subTest(test_email=test_email, tour_name=tour_name):
                test_partner = self.env['res.partner'].create({
                    'email': test_email,
                    'name': 'Test Déboulonneur'
                })
                self.assertFalse(test_partner.is_blacklisted)
                previous_messages = test_partner.message_ids
                test_email_normalized = tools.email_normalize(test_email)

                # launch unsubscription tour
                hash_token = test_mailing._generate_mailing_recipient_token(test_partner.id, test_partner.email_normalized)
                with freeze_time(self._reference_now):
                    self.start_tour(
                        f"/mailing/{test_mailing.id}/unsubscribe?email={test_partner.email_normalized}&document_id={test_partner.id}&hash_token={hash_token}",
                        tour_name,
                        login=None,
                    )

                # status update check
                self.assertTrue(test_partner.is_blacklisted)

                # partner (document): new message for blocklist addition with feedback
                self.assertEqual(len(test_partner.message_ids), len(previous_messages) + 1)
                msg_fb = test_partner.message_ids[0]
                self.assertEqual(
                    msg_fb.body,
                    Markup(f'<p>Feedback from {test_email_normalized}<br>{test_feedback}</p>')
                )

                # posted messages on exclusion list record: activated, feedback, deactivated, activated again
                bl_record = self.env['mail.blacklist'].search([('email', '=', test_partner.email_normalized)])
                self.assertEqual(len(bl_record.message_ids), 5)
                self.assertEqual(bl_record.opt_out_reason_id, opt_out_reasons[-1])
                msg_bl2, msg_unbl, msg_fb, msg_bl, msg_create = bl_record.message_ids
                self.assertEqual(
                    msg_bl2.body,
                    Markup(f'<p>Blocklist request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                           f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                           f'data-oe-model="{test_partner._name}" data-oe-id="{test_partner.id}">Contact</a>)</p>')
                )
                self.assertEqual(
                    msg_unbl.body,
                    Markup(f'<p>Blocklist removal request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                           f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                           f'data-oe-model="{test_partner._name}" data-oe-id="{test_partner.id}">Contact</a>)</p>')
                )
                self.assertEqual(
                    msg_fb.body,
                    Markup(f'<p>Feedback from {test_email_normalized}<br>{test_feedback}</p>')
                )
                self.assertTracking(msg_fb, [('opt_out_reason_id', 'many2one', False, opt_out_reasons[-1])])
                self.assertEqual(
                    msg_bl.body,
                    Markup(f'<p>Blocklist request from unsubscribe link of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                           f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                           f'data-oe-model="{test_partner._name}" data-oe-id="{test_partner.id}">Contact</a>)</p>')
                )
                self.assertEqual(msg_create.body, Markup('<p>Mail Blacklist created</p>'))

    def test_mailing_unsubscribe_from_document_tour_mailing_user(self):
        """ Test portal unsubscribe on mailings performed on documents (not
        mailing lists or contacts) using a generic '/unsubscribe' link allowing
        mailing users to see and edit unsubcribe page.

        Tour effects
          * unsubscribe from mailing based on a document = blocklist;
          * add feedback (block list): Other reason, with 'My feedback' feedback;
          * remove email from exclusion list;
          * re-add email to exclusion list;
        """
        # update user to link it with existing mailing contacts and allow the tour
        # to run; test without and with mailing group
        self.user_marketing.write({
            'email': tools.formataddr(("Déboulonneur", "fleurus@example.com")),
            'groups_id': [(3, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        test_mailing = self.test_mailing_on_documents.with_env(self.env)
        self.authenticate('user_marketing', 'user_marketing')

        # no group -> no direct access to /unsubscribe
        res = self.url_open(
            werkzeug.urls.url_join(
                test_mailing.get_base_url(),
                f'mailing/{test_mailing.id}/unsubscribe',
            )
        )
        self.assertEqual(res.status_code, 400)

        # group -> direct access to /unsubscribe should wokr
        self.user_marketing.write({
            'groups_id': [(4, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        # launch unsubscription tour
        with freeze_time(self._reference_now):
            self.start_tour(
                f"/mailing/{test_mailing.id}/unsubscribe",
                "mailing_portal_unsubscribe_from_document_with_lists",
                login=self.user_marketing.login,
            )

    def test_mailing_unsubscribe_from_list_tour(self):
        """ Test portal unsubscribe on mailings performed on mailing lists. Their
        effect is to opt-out from the mailing list.

        Tour effects
          * unsubscribe from mailing based on lists = opt-out from lists;
          * add feedback (opt-out): Other reason, with 'My feedback' feedback;
          * add email to exclusion list;
        """
        opt_out_reasons = self.env['mailing.subscription.optout'].search([])
        test_mailing = self.test_mailing_on_lists.with_env(self.env)
        test_feedback = "My feedback"

        # fetch contact and its subscription and blacklist status, to see the tour effects
        contact_l1 = self.mailing_list_1.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        subscription_l1 = self.mailing_list_1.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l1
        )

        # launch unsubscribe tour
        hash_token = test_mailing._generate_mailing_recipient_token(contact_l1.id, contact_l1.email)
        with freeze_time(self._reference_now):
            self.start_tour(
                f"/mailing/{test_mailing.id}/unsubscribe?email={self.test_email_normalized}&document_id={contact_l1.id}&hash_token={hash_token}",
                "mailing_portal_unsubscribe_from_list",
                login=None,
            )

        # status update check on list 1
        self.assertTrue(subscription_l1.opt_out)
        self.assertEqual(subscription_l1.opt_out_datetime, self._reference_now)
        self.assertEqual(subscription_l1.opt_out_reason_id, opt_out_reasons[-1])
        # status update check on list 2: unmodified (was not member, still not member)
        contact_l2 = self.mailing_list_2.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        self.assertFalse(contact_l2)

        # posted messages on contact record for mailing list 1: feedback, unsubscription
        message_feedback = contact_l1.message_ids[0]
        self.assertEqual(
            message_feedback.body,
            Markup(f'<p>Feedback from {contact_l1.email_normalized}<br>{test_feedback}</p>')
        )
        message_unsub = contact_l1.message_ids[1]
        self.assertEqual(
            message_unsub.body,
            Markup(f'<p>{contact_l1.display_name} unsubscribed from the following mailing list(s)</p><ul><li>{self.mailing_list_1.name}</li></ul>')
        )

        # posted messages on exclusion list record: activated, deactivated, activated again
        bl_record = self.env['mail.blacklist'].search([('email', '=', contact_l1.email_normalized)])
        self.assertEqual(len(bl_record.message_ids), 2)
        self.assertFalse(bl_record.opt_out_reason_id)
        msg_bl, msg_create = bl_record.message_ids
        self.assertEqual(
            msg_bl.body,
            Markup(f'<p>Blocklist request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                   f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                   f'data-oe-model="{contact_l1._name}" data-oe-id="{contact_l1.id}">Mailing Contact</a>)</p>')
        )
        self.assertEqual(msg_create.body, Markup('<p>Mail Blacklist created</p>'))

    def test_mailing_unsubscribe_from_list_with_update_tour(self):
        """ Test portal unsubscribe on mailings performed on mailing lists. Their
        effect is to opt-out from the mailing list. Optional exclusion list can
        be done through interface (see tour).

        Tour effects
          * unsubscribe from mailing based on lists = opt-out from lists;
          * add feedback (opt-out): Other reason, with 'My feedback' feedback;
          * add email to exclusion list;
          * remove email from exclusion list;
          * come back to List3;
          * join List2 (with no feedback, as no opt-out / block list was done);
          * re-add email to exclusion list;
        """
        opt_out_reasons = self.env['mailing.subscription.optout'].search([])
        test_mailing = self.test_mailing_on_lists.with_env(self.env)
        test_feedback = "My feedback"

        # fetch contact and its subscription and blacklist status, to see the tour effects
        contact_l1 = self.mailing_list_1.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        subscription_l1 = self.mailing_list_1.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l1
        )
        contact_l3 = self.mailing_list_3.contact_ids.filtered(
            lambda contact: contact.email == self.test_email_normalized
        )
        subscription_l3 = self.mailing_list_3.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l3
        )

        # launch unsubscription tour
        hash_token = test_mailing._generate_mailing_recipient_token(contact_l1.id, contact_l1.email)
        with freeze_time(self._reference_now):
            self.start_tour(
                f"/mailing/{test_mailing.id}/unsubscribe?email={contact_l1.email}&document_id={contact_l1.id}&hash_token={hash_token}",
                "mailing_portal_unsubscribe_from_list_with_update",
                login=None,
            )

        # status update check on list 1
        self.assertTrue(subscription_l1.opt_out)
        self.assertEqual(subscription_l1.opt_out_datetime, self._reference_now)
        self.assertEqual(subscription_l1.opt_out_reason_id, opt_out_reasons[-1])
        # status update check on list 3 (opt-in during test)
        self.assertFalse(subscription_l3.opt_out)
        self.assertFalse(subscription_l3.opt_out_datetime)

        # posted messages on contact record for mailing list 1: subscription update, feedback, unsubscription
        message_update = contact_l1.message_ids[0]
        self.assertEqual(
            message_update.body,
            Markup(f'<p>{contact_l1.display_name} subscribed to the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_2.name}</li></ul>')
        )
        message_feedback = contact_l1.message_ids[1]
        self.assertEqual(
            message_feedback.body,
            Markup(f'<p>Feedback from {contact_l1.email_normalized}<br>{test_feedback}</p>')
        )
        message_unsub = contact_l1.message_ids[2]
        self.assertEqual(
            message_unsub.body,
            Markup(f'<p>{contact_l1.display_name} unsubscribed from the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_1.name}</li></ul>')
        )

        # posted messages on contact record for mailing list 3: subscription
        message_sub = contact_l3.message_ids[0]
        self.assertEqual(
            message_sub.body,
            Markup(f'<p>{contact_l3.display_name} subscribed to the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_3.name}</li><li>{self.mailing_list_2.name}</li></ul>')
        )

        # posted messages on exclusion list record: activated, deactivated, activated again, feedback
        bl_record = self.env['mail.blacklist'].search([('email', '=', contact_l1.email_normalized)])
        self.assertEqual(bl_record.opt_out_reason_id, opt_out_reasons[0])
        self.assertEqual(len(bl_record.message_ids), 5)
        msg_fb, msg_bl2, msg_unbl, msg_bl, msg_create = bl_record.message_ids
        self.assertTracking(msg_fb, [('opt_out_reason_id', 'many2one', False, opt_out_reasons[0])])
        self.assertFalse(msg_fb.body)
        self.assertEqual(
            msg_bl2.body,
            Markup(f'<p>Blocklist request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                   f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                   f'data-oe-model="{contact_l1._name}" data-oe-id="{contact_l1.id}">Mailing Contact</a>)</p>')
        )
        self.assertEqual(
            msg_unbl.body,
            Markup(f'<p>Blocklist removal request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                   f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                   f'data-oe-model="{contact_l1._name}" data-oe-id="{contact_l1.id}">Mailing Contact</a>)</p>')
        )
        self.assertEqual(
            msg_bl.body,
            Markup(f'<p>Blocklist request from portal of mailing <a href="#" data-oe-model="{test_mailing._name}" '
                   f'data-oe-id="{test_mailing.id}">{test_mailing.subject}</a> (document <a href="#" '
                   f'data-oe-model="{contact_l1._name}" data-oe-id="{contact_l1.id}">Mailing Contact</a>)</p>')
        )
        self.assertEqual(msg_create.body, Markup('<p>Mail Blacklist created</p>'))

    def test_mailing_unsubscribe_from_my(self):
        """ Test portal unsubscribe using the 'my' mailing-specific portal page.
        It allows to opt-in / opt-out from mailing lists as well as to manage
        blocklist (see tour).

        Tour effects
          * opt-in List3 from opt-out, opt-in List2, opt-out List1;
          * add feedback (as new opt-out): Other reason, with 'My feedback' feedback;
          * add email in block list;
          * add feedback (as block list addition): First reason (hence no feedback);
        """
        test_feedback = "My feedback"
        portal_user = mail_new_test_user(
            self.env,
            email=tools.formataddr(("Déboulonneur", "fleurus@example.com")),
            groups='base.group_portal',
            login='user_portal_fleurus',
            name='Déboulonneur User',
            signature='--\nDéboulonneur',
        )
        _test_email, test_email_normalized = portal_user.email, portal_user.email_normalized
        opt_out_reasons = self.env['mailing.subscription.optout'].search([])

        # list opted-out and non-public should not be displayed
        private_list = self.env['mailing.list'].with_context(self._test_context).create({
            'contact_ids': [
                (0, 0, {'name': 'Déboulonneur User', 'email': 'fleurus@example.com'}),
            ],
            'name': 'List5',
            'is_public': False
        })
        private_list.subscription_ids[0].opt_out = True

        # launch 'my' mailing' tour
        self.authenticate(portal_user.login, portal_user.login)
        with freeze_time(self._reference_now):
            self.start_tour(
                "/mailing/my",
                "mailing_portal_unsubscribe_from_my",
                login=portal_user.login,
            )

        # fetch contact and its subscription and blacklist status, to see the tour effects
        contact_l1 = self.mailing_list_1.contact_ids.filtered(
            lambda contact: contact.email == test_email_normalized
        )
        subscription_l1 = self.mailing_list_1.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l1
        )
        contact_l2 = self.mailing_list_2.contact_ids.filtered(
            lambda contact: contact.email == test_email_normalized
        )
        subscription_l2 = self.mailing_list_2.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l2
        )
        contact_l3 = self.mailing_list_3.contact_ids.filtered(
            lambda contact: contact.email == test_email_normalized
        )
        subscription_l3 = self.mailing_list_3.subscription_ids.filtered(
            lambda subscription: subscription.contact_id == contact_l3
        )
        self.assertEqual(contact_l2, contact_l3,
                        'When creating new membership, should link with first found existing contact')
        self.assertTrue(contact_l1.is_blacklisted)
        self.assertTrue(contact_l3.is_blacklisted)
        self.assertTrue(subscription_l1.opt_out)
        self.assertEqual(subscription_l1.opt_out_datetime, self._reference_now,
                         'Subscription: opt-outed during test, datetime should have been set')
        self.assertEqual(subscription_l1.opt_out_reason_id, opt_out_reasons[-1])
        self.assertFalse(subscription_l2.opt_out)
        self.assertFalse(subscription_l2.opt_out_datetime)
        self.assertFalse(subscription_l2.opt_out_reason_id)
        self.assertFalse(subscription_l3.opt_out)
        self.assertFalse(subscription_l3.opt_out_datetime,
                         'Subscription: opt-in during test, datetime should have been reset')
        self.assertFalse(subscription_l3.opt_out_reason_id)
        # message on contact for list 1: opt-out L1, join L2
        msg_fb, msg_sub, msg_uns = contact_l1.message_ids
        self.assertEqual(
            msg_fb.body,
            Markup(f'<p>Feedback from {portal_user.name} ({test_email_normalized})<br>{test_feedback}</p>')
        )
        self.assertEqual(
            msg_sub.body,
            Markup(f'<p>{contact_l1.name} subscribed to the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_2.name}</li></ul>')
        )
        self.assertEqual(
            msg_uns.body,
            Markup(f'<p>{contact_l1.name} unsubscribed from the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_1.name}</li></ul>')
        )
        # message on contact for list 2: opt-in L3 and L2
        msg_fb, msg_sub = contact_l3.message_ids
        self.assertEqual(
            msg_fb.body,
            Markup(f'<p>Feedback from {portal_user.name} ({test_email_normalized})<br>{test_feedback}</p>')
        )
        self.assertEqual(
            msg_sub.body,
            Markup(f'<p>{contact_l3.name} subscribed to the following mailing list(s)</p>'
                   f'<ul><li>{self.mailing_list_3.name}</li><li>{self.mailing_list_2.name}</li></ul>')
        )

        # block list record created, feedback logged
        bl_record = self.env['mail.blacklist'].search([('email', '=', contact_l1.email_normalized)])
        self.assertEqual(bl_record.opt_out_reason_id, opt_out_reasons[0])
        self.assertEqual(len(bl_record.message_ids), 3)
        msg_fb, msg_bl, _msg_create = bl_record.message_ids
        self.assertTracking(msg_fb, [('opt_out_reason_id', 'many2one', False, opt_out_reasons[0])])
        self.assertEqual(msg_bl.body, Markup('<p>Blocklist request from portal</p>'))

    @mute_logger('odoo.http', 'odoo.addons.website.models.ir_ui_view')
    def test_mailing_view(self):
        """ Test preview of mailing. It requires either a token, either being
        mailing user. """
        test_mailing = self.test_mailing_on_documents.with_env(self.env)
        shadow_mailing = test_mailing.copy()
        doc_id, email_normalized = self.user_marketing.partner_id.id, self.user_marketing.email_normalized
        hash_token = test_mailing._generate_mailing_recipient_token(doc_id, email_normalized)
        self.user_marketing.write({
            'groups_id': [(3, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        self.authenticate('user_marketing', 'user_marketing')

        # TEST: various invalid cases
        for test_mid, test_doc_id, test_email, test_token, error_code in [
            (test_mailing.id, doc_id, email_normalized, '', 400),  # no token
            (test_mailing.id, doc_id, email_normalized, 'zboobs', 418),  # wrong token
            (test_mailing.id, self.env.user.partner_id.id, email_normalized, hash_token, 418),  # mismatch
            (test_mailing.id, doc_id, 'not.email@example.com', hash_token, 418),  # mismatch
            (shadow_mailing.id, doc_id, email_normalized, hash_token, 418),  # valid credentials but wrong mailing_id
            (0, doc_id, email_normalized, hash_token, 400),  # valid credentials but missing mailing_id
        ]:
            with self.subTest(test_mid=test_mid, test_email=test_email, test_doc_id=test_doc_id, test_token=test_token):
                res = self.url_open(
                    werkzeug.urls.url_join(
                        test_mailing.get_base_url(),
                        f'mailing/{test_mid}/view?email={test_email}&document_id={test_doc_id}&hash_token={test_token}',
                    )
                )
                self.assertEqual(res.status_code, error_code)

        # TEST: valid call using credentials
        res = self.url_open(
            werkzeug.urls.url_join(
                test_mailing.get_base_url(),
                f'mailing/{test_mailing.id}/view?email={email_normalized}&document_id={doc_id}&hash_token={hash_token}',
            )
        )
        self.assertEqual(res.status_code, 200)

        # TEST: invalid credentials but mailing user
        self.user_marketing.write({
            'groups_id': [(4, self.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })
        res = self.url_open(
            werkzeug.urls.url_join(
                test_mailing.get_base_url(),
                f'mailing/{test_mailing.id}/view',
            )
        )
        self.assertEqual(res.status_code, 200)


@tagged('link_tracker', 'mailing_portal')
class TestMailingTracking(TestMailingControllersCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mass_mailing.models.mailing')
    def test_tracking_short_code(self):
        """ Test opening short code linked to a mailing trace: should set the
        trace as opened and clicked, create a click record. """
        mailing = self.test_mailing_on_lists.with_env(self.env)
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        mail = self._find_mail_mail_wrecord(self.test_contact)
        mailing_trace = mail.mailing_trace_ids
        link_tracker_code = self._get_code_from_short_url(
            self._get_href_from_anchor_id(mail.body, 'url')
        )
        self.assertEqual(len(link_tracker_code), 1)
        self.assertEqual(link_tracker_code.link_id.count, 0)
        self.assertEqual(mail.state, 'sent')
        self.assertEqual(len(mailing_trace), 1)
        self.assertFalse(mailing_trace.links_click_datetime)
        self.assertFalse(mailing_trace.open_datetime)
        self.assertEqual(mailing_trace.trace_status, 'sent')

        short_link_url = werkzeug.urls.url_join(
            mail.get_base_url(),
            f'r/{link_tracker_code.code}/m/{mailing_trace.id}'
        )
        with freeze_time(self._reference_now):
            response = self.url_open(short_link_url, allow_redirects=False)
            self.assertTrue(response.headers['Location'].startswith('https://www.example.com/foo/bar?baz=qux'))

        self.assertEqual(link_tracker_code.link_id.count, 1)
        self.assertEqual(mailing_trace.links_click_datetime, self._reference_now)
        self.assertEqual(mailing_trace.open_datetime, self._reference_now)
        self.assertEqual(mailing_trace.trace_status, 'open')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mass_mailing.models.mailing')
    def test_tracking_url_token(self):
        """ Test tracking of mails linked to a mailing trace: should set the
        trace as opened. """
        mailing = self.test_mailing_on_lists.with_env(self.env)
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        mail = self._find_mail_mail_wrecord(self.test_contact)
        mail_id_int = mail.id
        mail_tracking_url = mail._get_tracking_url()
        mailing_trace = mail.mailing_trace_ids
        self.assertEqual(mail.state, 'sent')
        self.assertEqual(len(mailing_trace), 1)
        self.assertFalse(mailing_trace.open_datetime)
        self.assertEqual(mailing_trace.trace_status, 'sent')
        mail.unlink()  # the mail might be removed during the email sending
        self.env.flush_all()

        with freeze_time(self._reference_now):
            response = self.url_open(mail_tracking_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mailing_trace.open_datetime, self._reference_now)
        self.assertEqual(mailing_trace.trace_status, 'open')

        track_url = werkzeug.urls.url_join(
            mailing.get_base_url(),
            f'mail/track/{mail_id_int}/fake_token/blank.gif'
        )
        response = self.url_open(track_url)
        self.assertEqual(response.status_code, 401)
