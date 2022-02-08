# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from unittest.mock import patch
from unittest.mock import DEFAULT

from odoo import exceptions
from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.addons.sms.models.sms_sms import SmsSms as SmsSms
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon


class TestSMSPost(TestMailFullCommon, MockLinkTracker):

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

        # tracking info
        cls.utm_c = cls.env.ref('utm.utm_campaign_fall_drive')
        cls.utm_m = cls.env.ref('mass_mailing_sms.utm_medium_sms')
        cls.tracker_values = {
            'campaign_id': cls.utm_c.id,
            'medium_id': cls.utm_m.id,
        }

    def test_body_link_shorten(self):
        link = 'http://www.example.com'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertNotIn(link, new_body)
        self.assertLinkShortenedText(new_body, (link, True), {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name})
        link = self.env['link.tracker'].search([('url', '=', link)])
        self.assertIn(link.short_url, new_body)

        link = 'https://test.odoo.com/my/super_page?test[0]=42&toto=áâà#title3'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertNotIn(link, new_body)
        self.assertLinkShortenedText(new_body, (link, True), {
            'utm_campaign': self.utm_c.name,
            'utm_medium': self.utm_m.name,
            'test[0]': '42',
            'toto': 'áâà',
        })
        link = self.env['link.tracker'].search([('url', '=', link)])
        self.assertIn(link.short_url, new_body)
        # Bugfix: ensure void content convert does not crash
        new_body = self.env['mail.render.mixin']._shorten_links_text(False, self.tracker_values)
        self.assertFalse(new_body)

    def test_body_link_shorten_wshort(self):
        link = 'https://test.odoo.com/r/RAOUL'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertIn(link, new_body)
        self.assertFalse(self.env['link.tracker'].search([('url', '=', link)]))

    def test_body_link_shorten_wunsubscribe(self):
        link = 'https://test.odoo.com/sms/3/'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
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
            'number': '10',
            'mailing_id': mailing.id,
        })
        sms_1 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/r/RAOUL',
            'number': '11',
        })
        sms_2 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/r/RAOUL',
            'number': '12',
            'mailing_id': mailing.id,
        })
        sms_3 = self.env['sms.sms'].create({
            'body': 'Welcome to https://test.odoo.com/leodagan/r/RAOUL',
            'number': '13',
            'mailing_id': mailing.id,
        })

        res = (sms_0 | sms_1 | sms_2 | sms_3)._update_body_short_links()
        self.assertEqual(res[sms_0.id], 'Welcome to https://test.odoo.com')
        self.assertEqual(res[sms_1.id], 'Welcome to https://test.odoo.com/r/RAOUL')
        self.assertEqual(res[sms_2.id], 'Welcome to https://test.odoo.com/r/RAOUL/s/%s' % sms_2.id)
        self.assertEqual(res[sms_3.id], 'Welcome to https://test.odoo.com/leodagan/r/RAOUL')

    def test_sms_send_batch_size(self):
        self.count = 0

        def _send(sms_self, unlink_failed=False, unlink_sent=True, raise_exception=False):
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
        with self.mockSMSGateway(sms_allow_unlink=True, sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=True, unlink_sent=True, raise_exception=False)
        self.assertFalse(len(self.sms_all.exists()))

    def test_sms_send_delete_default(self):
        """ Test default send behavior: keep failed SMS, remove sent. """
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'credit',
                '+32456000033': 'server_error',
                '+32456000044': 'unregistered',
            }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(len(remaining), 4)
        self.assertTrue(all(sms.state == 'error') for sms in remaining)

    def test_sms_send_delete_failed(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
            }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=True, unlink_sent=False, raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(len(remaining), 8)
        self.assertTrue(all(sms.state == 'sent') for sms in remaining)

    def test_sms_send_delete_none(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
            }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=False, unlink_sent=False, raise_exception=False)
        self.assertEqual(len(self.sms_all.exists()), 10)
        success_sms = self.sms_all[:1] + self.sms_all[3:]
        error_sms = self.sms_all[1:3]
        self.assertTrue(all(sms.state == 'sent') for sms in success_sms)
        self.assertTrue(all(sms.state == 'error') for sms in error_sms)

    def test_sms_send_delete_sent(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
            }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=False, unlink_sent=True, raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(len(remaining), 2)
        self.assertTrue(all(sms.state == 'error') for sms in remaining)

    def test_sms_send_raise(self):
        with self.assertRaises(exceptions.AccessError):
            with self.mockSMSGateway(sim_error='jsonrpc_exception'):
                self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=True)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['outgoing']))

    def test_sms_send_raise_catch(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['error']))
