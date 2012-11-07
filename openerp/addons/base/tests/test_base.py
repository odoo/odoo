import unittest2

import openerp.tests.common as common

class test_base(common.TransactionCase):

    def setUp(self):
        super(test_base,self).setUp()
        self.res_partner = self.registry('res.partner')

        # samples use effective TLDs from the Mozilla public suffix
        # list at http://publicsuffix.org
        self.samples = [
            ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
            ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
            (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum')
        ]

    def test_00_res_partner_name_create(self):
        cr, uid = self.cr, self.uid
        parse = self.res_partner._parse_partner_name
        for text, name, mail in self.samples:
            self.assertEqual((name,mail), parse(text), 'Partner name parsing failed')
            partner_id, dummy = self.res_partner.name_create(cr, uid, text)
            partner = self.res_partner.browse(cr, uid, partner_id)
            self.assertEqual(name or mail, partner.name, 'Partner name incorrect')
            self.assertEqual(mail or False, partner.email, 'Partner email incorrect')

    def test_10_res_partner_find_or_create(self):
        cr,uid = self.cr, self.uid
        email = self.samples[0][0]
        partner_id, dummy = self.res_partner.name_create(cr, uid, email)
        found_id = self.res_partner.find_or_create(cr, uid, email)
        self.assertEqual(partner_id, found_id, 'find_or_create failed')
        new_id = self.res_partner.find_or_create(cr, uid, self.samples[1][0])
        self.assertTrue(new_id > partner_id, 'find_or_create failed - should have created new one')
        new_id2 = self.res_partner.find_or_create(cr, uid, self.samples[2][0])
        self.assertTrue(new_id2 > new_id, 'find_or_create failed - should have created new one again')


if __name__ == '__main__':
    unittest2.main()