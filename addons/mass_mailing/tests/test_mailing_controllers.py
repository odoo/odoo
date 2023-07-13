# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

import datetime
import werkzeug

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from requests import Session, PreparedRequest, Response

from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('link_tracker')
class TestMailingControllers(MassMailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailingControllers, cls).setUpClass()
        cls._create_mailing_list()
        cls.test_mailing = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/><br />Go to <a id="url" href="https://www.example.com/foo/bar?baz=qux">this link</a></p>',
            'contact_list_ids': [(4, cls.mailing_list_1.id), (4, cls.mailing_list_2.id)],
            'mailing_model_id': cls.env['ir.model']._get('mailing.list').id,
            'mailing_type': 'mail',
            'name': 'TestMailing',
            'reply_to': cls.email_reply_to,
            'subject': 'Test',
        })

        cls.test_contact = cls.mailing_list_1.contact_ids[0]

        # freeze time base value
        cls._reference_now = datetime.datetime(2022, 6, 14, 10, 0, 0)

    def _request_handler(self, s: Session, r: PreparedRequest, /, **kw):
        if r.url.startswith('https://www.example.com/foo/bar'):
            r = Response()
            r.status_code = 200
            return r
        return super()._request_handler(s, r, **kw)

    def test_tracking_short_code(self):
        """ Test opening short code linked to a mailing trace: should set the
        trace as opened and clicked, create a click record. """
        mailing = self.test_mailing.with_env(self.env)
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
            _response = self.url_open(short_link_url)

        self.assertEqual(link_tracker_code.link_id.count, 1)
        self.assertEqual(mailing_trace.links_click_datetime, self._reference_now)
        self.assertEqual(mailing_trace.open_datetime, self._reference_now)
        self.assertEqual(mailing_trace.trace_status, 'open')

    def test_tracking_url_token(self):
        """ Test tracking of mails linked to a mailing trace: should set the
        trace as opened. """
        mailing = self.test_mailing.with_env(self.env)
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
        self.assertEqual(response.status_code, 400)
