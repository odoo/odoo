# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
    ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@CHIRURGIENS-dentistes.fr'),
    ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
    ('"Patrick Da Beast Poilvache" <PATRICK@example.com>', 'Patrick Poilvache', 'patrick@example.com'),
    ('Patrick Caché <patrick@EXAMPLE.COM>', 'Patrick Poilvache', 'patrick@example.com'),
    ('Patrick Caché <2patrick@EXAMPLE.COM>', 'Patrick Caché', '2patrick@example.com'),

]

class TestPartner(TransactionCase):

    def _check_find_or_create(self, test_string, expected_name, expected_email, expected_email_normalized=False, check_partner=False, should_create=False):
        expected_email_normalized = expected_email_normalized or expected_email
        partner = self.env['res.partner'].find_or_create(test_string)
        if should_create and check_partner:
            self.assertTrue(partner.id > check_partner.id, 'find_or_create failed - should have found existing')
        elif check_partner:
            self.assertEqual(partner, check_partner, 'find_or_create failed - should have found existing')
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or '', expected_email)
        self.assertEqual(partner.email_normalized or '', expected_email_normalized)
        return partner

    def test_res_partner_find_or_create(self):
        Partner = self.env['res.partner']

        partner = Partner.browse(Partner.name_create(SAMPLES[0][0])[0])
        self._check_find_or_create(
            SAMPLES[0][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        partner_2 = Partner.browse(Partner.name_create('sarah.john@connor.com')[0])
        found_2 = self._check_find_or_create(
            'john@connor.com', 'john@connor.com', 'john@connor.com',
            check_partner=partner_2, should_create=True
        )

        new = self._check_find_or_create(
            SAMPLES[1][0], SAMPLES[1][2].lower(), SAMPLES[1][2].lower(),
            check_partner=found_2, should_create=True
        )

        new2 = self._check_find_or_create(
            SAMPLES[2][0], SAMPLES[2][1], SAMPLES[2][2],
            check_partner=new, should_create=True
        )

        self._check_find_or_create(
            SAMPLES[3][0], SAMPLES[3][1], SAMPLES[3][2],
            check_partner=new2, should_create=True
        )

        new4 = self._check_find_or_create(
            SAMPLES[4][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        self._check_find_or_create(
            SAMPLES[5][0], SAMPLES[5][1], SAMPLES[5][2],
            check_partner=new4, should_create=True
        )

        existing = Partner.create({
            'name': SAMPLES[6][1],
            'email': SAMPLES[6][0],
        })
        self.assertEqual(existing.name, SAMPLES[6][1])
        self.assertEqual(existing.email, SAMPLES[6][0])
        self.assertEqual(existing.email_normalized, SAMPLES[6][2])

        new6 = self._check_find_or_create(
            SAMPLES[7][0], SAMPLES[6][1], SAMPLES[6][0],
            expected_email_normalized=SAMPLES[6][2],
            check_partner=existing, should_create=False
        )

        self._check_find_or_create(
            SAMPLES[8][0], SAMPLES[8][1], SAMPLES[8][2],
            check_partner=new6, should_create=True
        )
