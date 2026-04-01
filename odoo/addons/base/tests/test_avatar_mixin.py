# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode

from odoo.tests.common import TransactionCase

class TestAvatarMixin(TransactionCase):

    """ tests the avatar mixin """
    def setUp(self):
        super().setUp()
        # Set partner manually to fake seed create_date
        partner_without_image = self.env['res.partner'].create({'name': 'Marc Demo', 'create_date': '2015-11-12 00:00:00'})
        self.user_without_image = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'create_date': '2015-11-12 00:00:00',
            'login': 'demo_1',
            'password': 'demo_1',
            'partner_id': partner_without_image.id,
        })
        self.user_without_name = self.env['res.users'].create({
            'name': '',
            'email': 'marc.grey25@example.com',
            'image_1920': False,
            'login': 'marc_1',
            'password': 'marc_1',
        })
        self.external_partner = self.env['res.partner'].create({
            'name': 'Josh Demo',
            'email': 'josh.brown23@example.com',
            'image_1920': False,
            'create_date': '2015-11-12 00:00:00',
        })

    def test_partner_has_avatar_even_if_it_has_no_image(self):
        self.assertTrue(self.user_without_image.partner_id.avatar_128)
        self.assertTrue(self.user_without_image.partner_id.avatar_256)
        self.assertTrue(self.user_without_image.partner_id.avatar_512)
        self.assertTrue(self.user_without_image.partner_id.avatar_1024)
        self.assertTrue(self.user_without_image.partner_id.avatar_1920)

    def test_content_of_generated_partner_avatar(self):
        expectedAvatar = (
            "<?xml version='1.0' encoding='UTF-8' ?>"
            "<svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            "<rect fill='hsl(184, 40%, 45%)' height='180' width='180'/>"
            "<text fill='#ffffff' font-size='96' text-anchor='middle' x='90' y='125' font-family='sans-serif'>M</text>"
            "</svg>"
        )
        self.assertEqual(expectedAvatar, b64decode(self.user_without_image.partner_id.avatar_1920).decode('utf-8'))

    def test_partner_without_name_has_default_placeholder_image_as_avatar(self):
        self.assertEqual(self.user_without_name.partner_id._avatar_get_placeholder(), b64decode(self.user_without_name.partner_id.avatar_1920))

    def test_external_partner_has_default_placeholder_image_as_avatar(self):
        expectedAvatar = (
            "<?xml version='1.0' encoding='UTF-8' ?>"
            "<svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            "<rect fill='hsl(71, 48%, 45%)' height='180' width='180'/>"
            "<text fill='#ffffff' font-size='96' text-anchor='middle' x='90' y='125' font-family='sans-serif'>J</text>"
            "</svg>"
        )
        self.assertEqual(expectedAvatar, b64decode(self.external_partner.avatar_1920).decode('utf-8'))

    def test_partner_and_user_have_the_same_avatar(self):
        self.assertEqual(self.user_without_image.partner_id.avatar_1920, self.user_without_image.avatar_1920)
