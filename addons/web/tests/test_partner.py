# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import unittest

from odoo.tests.common import HttpCase, tagged
from base64 import b64decode

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, vcard file generation disabled. Consider installing this module if you want to generate vcard files")
    vobject = None


@tagged('-at_install', 'post_install')
class TestPartnerVCard(HttpCase):

    def setUp(self):
        super().setUp()

        if not vobject:
            raise unittest.SkipTest("Skip tests when `vobject` Python module is not found.")

        self.partner = self.env['res.partner'].create({
            'name': 'John Doe',
            'email': 'john.doe@test.example.com',
            'mobile': '+1 202 555 0888',
            'phone': '+1 202 555 0122',
            'function': 'Painter',
            'street': 'Cookieville Minimum-Security Orphanarium',
            'city': 'New York',
            'country_id': self.env.ref('base.us').id,
            'zip': '97648',
            'website': 'https://test.exemple.com',
        })
        self.authenticate("admin", "admin")

    def test_fetch_partner_vcard(self):
        res = self.url_open('/web/partner/%d/vcard' % self.partner.id)
        vcard = vobject.readOne(res.text)
        self.assertEqual(vcard.contents["n"][0].value.family, self.partner.name, "Vcard should have the same name")
        self.assertEqual(vcard.contents["adr"][0].value.street, self.partner.street, "Vcard should have the same street")
        self.assertEqual(vcard.contents["adr"][0].value.city, self.partner.city, "Vcard should have the same city")
        self.assertEqual(vcard.contents["adr"][0].value.code, self.partner.zip, "Vcard should have the same zip")
        self.assertEqual(vcard.contents["adr"][0].value.country, self.env.ref('base.us').name, "Vcard should have the same country")
        self.assertEqual(vcard.contents["email"][0].value, self.partner.email, "Vcard should have the same email")
        self.assertEqual(vcard.contents["url"][0].value, self.partner.website, "Vcard should have the same website")
        self.assertEqual(vcard.contents["tel"][0].params['TYPE'], ["work"], "Vcard should have the same phone")
        self.assertEqual(vcard.contents["tel"][0].value, self.partner.phone, "Vcard should have the same phone")
        self.assertEqual(vcard.contents["tel"][1].params['TYPE'], ["cell"], "Vcard should have the same mobile")
        self.assertEqual(vcard.contents["tel"][1].value, self.partner.mobile, "Vcard should have the same mobile")
        self.assertEqual(vcard.contents["title"][0].value, self.partner.function, "Vcard should have the same function")
        self.assertEqual(len(vcard.contents['photo'][0].value), len(b64decode(self.partner.avatar_512)), "Vcard should have the same photo")

    @unittest.skip
    def test_not_exist_partner_vcard(self):
        partner_id = self.partner.id
        self.partner.unlink()
        res = self.url_open('/web/partner/%d/vcard' % partner_id)
        self.assertEqual(res.status_code, 404)
