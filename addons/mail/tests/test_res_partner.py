# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPartner(TransactionCase):

    def test_res_partner_find_or_create(self):
        Partner = self.env['res.partner']

        existing = Partner.create({
            'name': 'Patrick Poilvache',
            'email': '"Patrick Da Beast Poilvache" <PATRICK@example.com>',
        })
        self.assertEqual(existing.name, 'Patrick Poilvache')
        self.assertEqual(existing.email, '"Patrick Da Beast Poilvache" <PATRICK@example.com>')
        self.assertEqual(existing.email_normalized, 'patrick@example.com')

        new = Partner.find_or_create('Patrick Caché <patrick@EXAMPLE.COM>')
        self.assertEqual(new, existing)

        new2 = Partner.find_or_create('Patrick Caché <2patrick@EXAMPLE.COM>')
        self.assertTrue(new2.id > new.id)
        self.assertEqual(new2.name, 'Patrick Caché')
        self.assertEqual(new2.email, '2patrick@example.com')
        self.assertEqual(new2.email_normalized, '2patrick@example.com')
