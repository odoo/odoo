# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from unittest.mock import patch
from unittest.mock import DEFAULT

from odoo import exceptions
from odoo.addons.sms.models.sms_sms import SmsSms as SmsSms
from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common
from odoo.tests import common


class LinkTrackerMock(common.BaseCase):

    def setUp(self):
        super(LinkTrackerMock, self).setUp()

        def _compute_favicon():
            # 1px to avoid real request
            return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='

        def _get_title_from_url(u):
            return "Test_TITLE"

        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://test.odoo.com')

        link_tracker_favicon_patch = patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker._compute_favicon', wraps=_compute_favicon)
        link_tracker_title_patch = patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker._get_title_from_url', wraps=_get_title_from_url)
        link_tracker_favicon_patch.start()
        link_tracker_title_patch.start()
        self.addCleanup(link_tracker_favicon_patch.stop)
        self.addCleanup(link_tracker_title_patch.stop)

        self.utm_c = self.env.ref('utm.utm_campaign_fall_drive')
        self.utm_m = self.env.ref('mass_mailing_sms.utm_medium_sms')
        self.tracker_values = {
            'campaign_id': self.utm_c.id,
            'medium_id': self.utm_m.id,
        }

    def assertLinkTracker(self, url, url_params):
        links = self.env['link.tracker'].sudo().search([('url', '=', url)])
        self.assertEqual(len(links), 1)

        # check UTMS are correctly set on redirect URL
        original_url = werkzeug.urls.url_parse(url)
        redirect_url = werkzeug.urls.url_parse(links.redirected_url)
        redirect_params = redirect_url.decode_query().to_dict(flat=True)
        self.assertEqual(redirect_url.scheme, original_url.scheme)
        self.assertEqual(redirect_url.decode_netloc(), original_url.decode_netloc())
        self.assertEqual(redirect_url.path, original_url.path)
        self.assertEqual(redirect_params, url_params)


class TestSMSPost(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, LinkTrackerMock):

    @classmethod
    def setUpClass(cls):
        super(TestSMSPost, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.sms_all = cls.env['sms.sms']
        for x in range(10):
            cls.sms_all |= cls.env['sms.sms'].create({
                'number': '+324560000%s%s' % (x, x),
                'body': cls._test_body,
            })

    def test_body_link_shorten(self):
        link = 'http://www.example.com'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['link.tracker']._convert_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertNotIn(link, new_body)
        self.assertLinkTracker(link, {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name})
        link = self.env['link.tracker'].search([('url', '=', link)])
        self.assertIn(link.short_url, new_body)

        link = 'https://test.odoo.com/my/super_page?test[0]=42&toto=áâà#title3'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['link.tracker']._convert_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertNotIn(link, new_body)
        self.assertLinkTracker(link, {
            'utm_campaign': self.utm_c.name,
            'utm_medium': self.utm_m.name,
            'test[0]': '42',
            'toto': 'áâà',
        })
        link = self.env['link.tracker'].search([('url', '=', link)])
        self.assertIn(link.short_url, new_body)

    def test_body_link_shorten_wshort(self):
        link = 'https://test.odoo.com/r/RAOUL'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['link.tracker']._convert_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertIn(link, new_body)
        self.assertFalse(self.env['link.tracker'].search([('url', '=', link)]))

    def test_body_link_shorten_wunsubscribe(self):
        link = 'https://test.odoo.com/sms/3/'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['link.tracker']._convert_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertIn(link, new_body)
        self.assertFalse(self.env['link.tracker'].search([('url', '=', link)]))

    def test_sms_body_link_shorten_suffix(self):
        mailing = self.env['mailing.mailing'].create({
            'subject': 'Minimal mailing',
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
            'mailing_type': 'sms',
        })

        sms_0 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com',
            'number': '12',
            'mailing_id': mailing.id,
        })
        sms_1 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/r/RAOUL',
            'number': '12',
        })
        sms_2 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/r/RAOUL',
            'number': '12', 'mailing_id': mailing.id,
        })
        sms_3 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/leodagan/r/RAOUL',
            'number': '12', 'mailing_id': mailing.id,
        })

        res = (sms_0 | sms_1 | sms_2 | sms_3)._update_body_short_links()
        self.assertEqual(res[sms_0.id], 'Welcome to https://test.odoo.com')
        self.assertEqual(res[sms_1.id], 'Welcome to https://test.odoo.com/r/RAOUL')
        self.assertEqual(res[sms_2.id], 'Welcome to https://test.odoo.com/r/RAOUL/s/%s' % sms_2.id)
        self.assertEqual(res[sms_3.id], 'Welcome to https://test.odoo.com/leodagan/r/RAOUL')

    def test_sms_send_batch_size(self):
        self.count = 0

        def _send(sms_self, delete_all=False, raise_exception=False):
            self.count += 1
            return DEFAULT

        self.env['ir.config_parameter'].set_param('sms.session.batch.size', '3')
        with patch.object(SmsSms, '_send', autospec=True, side_effect=_send) as send_mock:
            self.env['sms.sms'].browse(self.sms_all.ids).send()

        self.assertEqual(self.count, 4)

    def test_sms_send_crash_employee(self):
        with self.assertRaises(exceptions.AccessError):
            self.env['sms.sms'].with_user(self.user_employee).browse(self.sms_all.ids).send()

    def test_sms_send_delete_all(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(delete_all=True, raise_exception=False)
        self.assertFalse(len(self.sms_all.exists()))

    def test_sms_send_raise(self):
        with self.assertRaises(exceptions.AccessError):
            with self.mockSMSGateway(sim_error='jsonrpc_exception'):
                self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=True)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['outgoing']))

    def test_sms_send_raise_catch(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['error']))
