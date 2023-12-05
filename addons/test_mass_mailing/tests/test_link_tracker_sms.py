# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.tests import tagged


@tagged('link_tracker')
class TestSMSPost(TestMassMailCommon):

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
        cls.utm_c = cls.env['utm.campaign'].create({
            'name': 'UTM C',
            'stage_id': cls.env.ref('utm.default_utm_stage').id,
            'is_auto_campaign': True,
        })
        cls.utm_m = cls.env.ref('mass_mailing_sms.utm_medium_sms')
        cls.tracker_values = {
            'campaign_id': cls.utm_c.id,
            'medium_id': cls.utm_m.id,
        }

    def setUp(self):
        super(TestSMSPost, self).setUp()
        self._web_base_url = 'https://test.odoo.com'
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', self._web_base_url)

    def test_body_link_shorten(self):
        link = 'http://www.example.com'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertNotIn(link, new_body)
        self.assertLinkShortenedText(new_body, (link, True), {'utm_campaign': self.utm_c.name, 'utm_medium': self.utm_m.name})
        link = self.env['link.tracker'].search([('url', '=', link)])
        self.assertIn(link.short_url, new_body)

        link = f'{self._web_base_url}/my/super_page?test[0]=42&toto=áâà#title3'
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
        link = f'{self._web_base_url}/r/RAOUL'
        self.env['link.tracker'].search([('url', '=', link)]).unlink()
        new_body = self.env['mail.render.mixin']._shorten_links_text('Welcome to %s !' % link, self.tracker_values)
        self.assertIn(link, new_body)
        self.assertFalse(self.env['link.tracker'].search([('url', '=', link)]))

    def test_body_link_shorten_wunsubscribe(self):
        link = f'{self._web_base_url}/sms/3/'
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
            'body': f'Welcome to {self._web_base_url}',
            'number': '10',
            'mailing_id': mailing.id,
        })
        sms_1 = self.env['sms.sms'].create({
            'body': f'Welcome to {self._web_base_url}/r/RAOUL',
            'number': '11',
        })
        sms_2 = self.env['sms.sms'].create({
            'body': f'Welcome to {self._web_base_url}/r/RAOUL',
            'number': '12',
            'mailing_id': mailing.id,
        })
        sms_3 = self.env['sms.sms'].create({
            'body': f'Welcome to {self._web_base_url}/leodagan/r/RAOUL',
            'number': '13',
            'mailing_id': mailing.id,
        })
        sms_4 = self.env['sms.sms'].create({
            'body': f'Welcome to {self._web_base_url}/r/RAOUL\nAnd again,\n'
                    f'{self._web_base_url}/r/RAOUL',
            'number': '14',
            'mailing_id': mailing.id,
        })

        res = (sms_0 | sms_1 | sms_2 | sms_3 | sms_4)._update_body_short_links()
        self.assertEqual(res[sms_0.id], f'Welcome to {self._web_base_url}')
        self.assertEqual(res[sms_1.id], f'Welcome to {self._web_base_url}/r/RAOUL')
        self.assertEqual(res[sms_2.id], f'Welcome to {self._web_base_url}/r/RAOUL/s/%s' % sms_2.id)
        self.assertEqual(res[sms_3.id], f'Welcome to {self._web_base_url}/leodagan/r/RAOUL')
        self.assertEqual(
            res[sms_4.id],
            f'Welcome to {self._web_base_url}/r/RAOUL/s/{sms_4.id}\nAnd again,\n{self._web_base_url}/r/RAOUL/s/{sms_4.id}')
