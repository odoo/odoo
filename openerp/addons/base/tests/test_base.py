import unittest2

import openerp.tests.common as common

class test_base(common.TransactionCase):

    def setUp(self):
        super(test_base,self).setUp()
        self.res_partner = self.registry('res.partner')

    def test_00_res_partner_name_parse(self):
        parse = self.res_partner._parse_partner_name
        # samples use effective TLDs from the Mozilla public suffix
        # list at http://publicsuffix.org
        test_samples = [
            ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
            ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
            (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum')
        ]
        for text, name, mail in test_samples:
            self.assertEqual((name,mail), parse(text), 'Partner name parsing failed')


if __name__ == '__main__':
    unittest2.main()