# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
import unittest
import zipfile
from odoo.fields import Command

from odoo.tests.common import HttpCase, tagged
from base64 import b64decode

from odoo.tools import mute_logger
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

        self.partners = self.env['res.partner'].create([{
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
        }, {
            'name': 'shut',
            'email': 'shut@test.example.com',
            'mobile': '+1 202 555 0999',
            'phone': '+1 202 555 0123',
            'function': 'Developer',
            'street': 'Donutville Maximum-Security Orphanarium',
            'city': 'Washington DC',
            'country_id': self.env.ref('base.us').id,
            'zip': '97649',
            'website': 'https://test.example.com',
            'child_ids': [
                Command.create({'type': 'other'})
            ]
        }])
        self.authenticate("admin", "admin")

    def check_vcard_contents(self, vcard, partner):
        self.assertEqual(vcard.contents["n"][0].value.family, partner.name, "Vcard should have the same name")
        self.assertEqual(vcard.contents["adr"][0].value.street, partner.street, "Vcard should have the same street")
        self.assertEqual(vcard.contents["adr"][0].value.city, partner.city, "Vcard should have the same city")
        self.assertEqual(vcard.contents["adr"][0].value.code, partner.zip, "Vcard should have the same zip")
        self.assertEqual(vcard.contents["adr"][0].value.country, self.env.ref('base.us').name, "Vcard should have the same country")
        self.assertEqual(vcard.contents["email"][0].value, partner.email, "Vcard should have the same email")
        self.assertEqual(vcard.contents["url"][0].value, partner.website, "Vcard should have the same website")
        self.assertEqual(vcard.contents["tel"][0].params['TYPE'], ["work"], "Vcard should have the same phone")
        self.assertEqual(vcard.contents["tel"][0].value, partner.phone, "Vcard should have the same phone")
        self.assertEqual(vcard.contents["tel"][1].params['TYPE'], ["cell"], "Vcard should have the same mobile")
        self.assertEqual(vcard.contents["tel"][1].value, partner.mobile, "Vcard should have the same mobile")
        self.assertEqual(vcard.contents["title"][0].value, partner.function, "Vcard should have the same function")
        self.assertEqual(len(vcard.contents['photo'][0].value), len(b64decode(partner.avatar_512)), "Vcard should have the same photo")

    def test_fetch_single_partner_vcard(self):
        res = self.url_open('/web_enterprise/partner/%d/vcard' % self.partners[0].id)
        vcard = vobject.readOne(res.text)
        self.check_vcard_contents(vcard, self.partners[0])

    def test_fetch_multiple_partners_vcard(self):
        res = self.url_open('/web/partner/vcard?partner_ids=%s,%s'
                            % (self.partners[0].id, self.partners[1].id))
        with io.BytesIO(res.content) as buffer:
            with zipfile.ZipFile(buffer, 'r') as zipf:
                vcfFileList = zipf.namelist()
                for i, vcfFile in enumerate(vcfFileList):
                    vcardFile = zipf.read(vcfFile).decode()
                    self.check_vcard_contents(vobject.readOne(vcardFile), self.partners[i])

    @unittest.skip
    def test_not_exist_partner_vcard(self):
        partner_id = self.partner.id
        self.partner.unlink()
        res = self.url_open('/web/partner/%d/vcard' % partner_id)
        self.assertEqual(res.status_code, 404)

    def test_check_partner_access_for_user(self):
        self.env['res.users'].create({
            'groups_id': [Command.set([self.env.ref('base.group_public').id])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.authenticate('testuser', 'testuser')
        with mute_logger('odoo.http'):  # mute 403 warning
            res = self.url_open('/web/partner/vcard?partner_ids=%s,%s' %
                            (self.partners[0].id, self.partners[1].id))
        self.assertEqual(res.status_code, 403)

    def test_fetch_single_partner_vcard_without_name(self):
        """
        Test to fetch a vcard of a partner create through
        child of another partner without name
        """
        partner = self.partners[1].child_ids[0]
        res = self.url_open('/web/partner/vcard?partner_ids=%s' % partner.id)
        vcard = vobject.readOne(res.text)
        self.assertEqual(vcard.contents["n"][0].value.family, partner.complete_name, "Vcard will have the complete name when it dosen't have name")
