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

    def test_letter_address_follows_country_format(self):
        """ With two street lines, a letter merges them on one line and keeps the country format
        for the rest of the address. """
        partner = self.env['res.partner'].new({
            'street': 'Hrusovska 455/10',
            'street2': 'Building B',
            'zip': '102 00',
            'city': 'Praha',
            'country_id': self.env.ref('base.cz').id,
        })
        self.assertEqual(
            partner.with_context(snailmail_layout=True)._display_address(),
            'Hrusovska 455/10, Building B\n102 00 Praha\nCzech Republic',
        )

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
