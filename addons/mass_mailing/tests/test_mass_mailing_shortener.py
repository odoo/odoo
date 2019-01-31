# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from lxml import etree

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestMassMailingShortener(common.TransactionCase):
    def getHrefFor(self, html, id):
        return html.xpath("*[@id='%s']" % id)[0].attrib.get('href')

    def shorturl_to_link(self, short_url):
        return self.env['link.tracker.code'].search([('code', '=', short_url.split('/r/')[-1])]).link_id

    def setUp(self):
        super(TestMassMailingShortener, self).setUp()

        def _get_title_from_url(u):
            return "Hello"

        def _compute_favicon():
            # 1px to avoid real request
            return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='

        patcher = patch('odoo.addons.link_tracker.models.link_tracker.link_tracker._compute_favicon', wraps=_compute_favicon)
        patcher2 = patch('odoo.addons.link_tracker.models.link_tracker.link_tracker._get_title_from_url', wraps=_get_title_from_url)
        patcher.start()
        patcher2.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(patcher2.stop)

    def test_00_test_mass_mailing_shortener(self):
        mailing_list_A = self.env['mail.mass_mailing.list'].create({
            'name': 'A',
        })
        self.env['mail.mass_mailing.contact'].create({
            'name': 'User 1', 'email': 'user1@example.com', 'list_ids': [(4, mailing_list_A.id)]
        })
        self.env['mail.mass_mailing.contact'].create({
            'name': 'User 2', 'email': 'user2@example.com', 'list_ids': [(4, mailing_list_A.id)]
        })
        self.env['mail.mass_mailing.contact'].create({
            'name': 'User 3', 'email': 'user3@example.com', 'list_ids': [(4, mailing_list_A.id)]
        })

        mass_mailing = self.env['mail.mass_mailing'].create({
            "reply_to_mode": "email",
            "reply_to": "Administrator <admin@yourcompany.example.com>",
            "mailing_model_id": self.env.ref('mass_mailing.model_mail_mass_mailing_list').id,
            "mailing_domain": "[('list_ids', 'in', [%d])]" % mailing_list_A.id,
            "contact_list_ids": [[6, False, [mailing_list_A.id]]],
            "mass_mailing_campaign_id": False,
            "name": "sdf",
            "body_html": """
Hi,
% set url = "www.odoo.com"
% set httpurl = "https://www.odoo.eu"
Website0: <a id="url0" href="https://www.odoo.tz/my/${object.name}">https://www.odoo.tz/my/${object.name}</h1>
Website1: <a id="url1" href="https://www.odoo.be">https://www.odoo.be</h1>
Website2: <a id="url2" href="https://${url}">https://${url}</h1>
Website3: <a id="url3" href="${httpurl}">${httpurl}</h1>
Email: <a id="url4" href="mailto:test@odoo.com">test@odoo.com</h1>
            """,
            "schedule_date": False,
            "state": "draft",
            "keep_archives": True,
        })

        mass_mailing.put_in_queue()
        mass_mailing._process_mass_mailing_queue()

        sent_mails = self.env['mail.mail'].search([('mailing_id', '=', mass_mailing.id)])
        sent_messages = sent_mails.mapped('mail_message_id')

        self.assertEqual(mailing_list_A.contact_nbr, len(sent_messages),
                         'Some message has not been sent')

        xbody = etree.fromstring(sent_messages[0].body)
        after_url0 = self.getHrefFor(xbody, 'url0')
        after_url1 = self.getHrefFor(xbody, 'url1')
        after_url2 = self.getHrefFor(xbody, 'url2')
        after_url3 = self.getHrefFor(xbody, 'url3')
        after_url4 = self.getHrefFor(xbody, 'url4')

        self.assertTrue('/r/' in after_url0, 'URL0 should be shortened: %s' % after_url0)
        self.assertTrue('/r/' in after_url1, 'URL1 should be shortened: %s' % after_url1)
        self.assertTrue('/r/' in after_url2, 'URL2 should be shortened: %s' % after_url2)
        self.assertTrue('/r/' in after_url3, 'URL3 should be shortened: %s' % after_url3)
        self.assertEqual(after_url4, "mailto:test@odoo.com", 'mailto: has been converted')

        short0 = self.shorturl_to_link(after_url0)
        short1 = self.shorturl_to_link(after_url1)
        short2 = self.shorturl_to_link(after_url2)
        short3 = self.shorturl_to_link(after_url3)

        self.assertTrue("https://www.odoo.tz/my/User" in short0.url, 'URL mismatch')
        self.assertEqual(short1.url, "https://www.odoo.be", 'URL mismatch')
        self.assertEqual(short2.url, "https://www.odoo.com", 'URL mismatch')
        self.assertEqual(short3.url, "https://www.odoo.eu", 'URL mismatch')

        _xbody = etree.fromstring(sent_messages[1].body)
        _after_url0 = self.getHrefFor(_xbody, 'url0')
        _after_url1 = self.getHrefFor(_xbody, 'url1')
        _after_url2 = self.getHrefFor(_xbody, 'url2')
        _after_url3 = self.getHrefFor(_xbody, 'url3')
        _after_url4 = self.getHrefFor(_xbody, 'url4')

        self.assertTrue('/r/' in _after_url0, 'URL0 should be shortened: %s' % _after_url0)
        self.assertTrue('/r/' in _after_url1, 'URL1 should be shortened: %s' % _after_url1)
        self.assertTrue('/r/' in _after_url2, 'URL2 should be shortened: %s' % _after_url2)
        self.assertTrue('/r/' in _after_url3, 'URL3 should be shortened: %s' % _after_url3)
        self.assertEqual(_after_url4, "mailto:test@odoo.com", 'mailto: has been converted')

        _short0 = self.shorturl_to_link(_after_url0)
        _short1 = self.shorturl_to_link(_after_url1)
        _short2 = self.shorturl_to_link(_after_url2)
        _short3 = self.shorturl_to_link(_after_url3)

        self.assertTrue("https://www.odoo.tz/my/User" in _short0.url, 'URL mismatch')
        self.assertEqual(_short1.url, "https://www.odoo.be", 'URL mismatch')
        self.assertEqual(_short2.url, "https://www.odoo.com", 'URL mismatch')
        self.assertEqual(_short3.url, "https://www.odoo.eu", 'URL mismatch')

        self.assertNotEqual(short0.url, _short0.url)
        self.assertEqual(short1.url, _short1.url)
        self.assertEqual(short2.url, _short2.url)
        self.assertEqual(short3.url, _short3.url)
