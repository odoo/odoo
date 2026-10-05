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
