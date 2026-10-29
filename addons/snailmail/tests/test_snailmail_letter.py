# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestSnailmailLetter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_de = cls.env['res.partner'].create({
            'name': 'Max Mustermann',
            'zip': '10115',
            'city': 'Musterstadt',
            'country_id': cls.env.ref('base.de').id,
        })
        cls.partner_ch = cls.env['res.partner'].create({
            'name': 'Jean Dupont',
            'street': 'Route de Lavaux 1',
            'street2': 'Appartement 3',
            'zip': '1095',
            'city': 'Lutry',
            'state_id': cls.env.ref('base.state_ch_vd_fr').id,
            'country_id': cls.env.ref('base.ch').id,
        })
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'John Doe',
            'street': '1 Main Street',
            'street2': 'Suite 100',
            'zip': '94105',
            'city': 'San Francisco',
            'state_id': cls.env.ref('base.state_us_5').id,
            'country_id': cls.env.ref('base.us').id,
        })

    def test_cover_address_split_germany(self):
        """ German cover addresses put both street lines on a single line separated by ' // '
        (Pingen requirement) and must keep a single zip/city line. """
        for street, street2, street_lines in [
            ('Hauptstrasse 6', False, ['Hauptstrasse 6']),
            ('Hauptstrasse 6', 'OT Nebenort', ['Hauptstrasse 6 // OT Nebenort']),
            (False, 'OT Nebenort', ['OT Nebenort']),
            (False, False, []),
        ]:
            with self.subTest(street=street, street2=street2):
                self.partner_de.write({'street': street, 'street2': street2})
                # display_name (with show_address) does not depend on the street fields
                self.partner_de.invalidate_recordset(['display_name'])
                letter = self.env['snailmail.letter'].create({
                    'model': self.partner_de._name,
                    'res_id': self.partner_de.id,
                    'partner_id': self.partner_de.id,
                })
                self.assertEqual(
                    letter._get_cover_address_split(),
                    ['Max Mustermann', *street_lines, '10115 Musterstadt', 'Germany'],
                )

    def test_snailmail_address_format_street2(self):
        """ When street2 is set, both street lines are merged on a single line but the
        country address format (zip/city order, no state) must be kept (Pingen requirement). """
        for partner, expected in [
            (self.partner_ch, "Route de Lavaux 1, Appartement 3\n1095 Lutry\nSwitzerland"),
            (self.partner_us, "1 Main Street, Suite 100\nSan Francisco CA 94105\nUnited States of America"),
        ]:
            with self.subTest(country=partner.country_id.code):
                self.assertEqual(
                    partner.with_context(snailmail_layout=True, lang='en_US')._display_address(),
                    expected,
                )
