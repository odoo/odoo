import unittest2

import openerp.tests.common as common
from openerp.osv.orm import except_orm

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


class test_partner_recursion(common.TransactionCase):

    def setUp(self):
        super(test_partner_recursion,self).setUp()
        self.res_partner = self.registry('res.partner')
        cr, uid = self.cr, self.uid
        self.p1 = self.res_partner.name_create(cr, uid, 'Elmtree')[0]
        self.p2 = self.res_partner.create(cr, uid, {'name': 'Elmtree Child 1', 'parent_id': self.p1})
        self.p3 = self.res_partner.create(cr, uid, {'name': 'Elmtree Grand-Child 1.1', 'parent_id': self.p2})

    # split 101, 102, 103 tests to force SQL rollback between them

    def test_101_res_partner_recursion(self):
        cr, uid, p1, p3 = self.cr, self.uid, self.p1, self.p3
        self.assertRaises(except_orm, self.res_partner.write, cr, uid, [p1], {'parent_id': p3})

    def test_102_res_partner_recursion(self):
        cr, uid, p2, p3 = self.cr, self.uid, self.p2, self.p3
        self.assertRaises(except_orm, self.res_partner.write, cr, uid, [p2], {'parent_id': p3})

    def test_103_res_partner_recursion(self):
        cr, uid, p3 = self.cr, self.uid, self.p3
        self.assertRaises(except_orm, self.res_partner.write, cr, uid, [p3], {'parent_id': p3})

    def test_104_res_partner_recursion_indirect_cycle(self):
        """ Indirect hacky write to create cycle in children """
        cr, uid, p2, p3 = self.cr, self.uid, self.p2, self.p3
        p3b = self.res_partner.create(cr, uid, {'name': 'Elmtree Grand-Child 1.2', 'parent_id': self.p2})
        self.assertRaises(except_orm, self.res_partner.write, cr, uid, [p2],
                          {'child_ids': [(1, p3, {'parent_id': p3b}), (1, p3b, {'parent_id': p3})]})

    def test_110_res_partner_recursion_multi_update(self):
        """ multi-write on several partners in same hierarchy must not trigger a false cycle detection """
        cr, uid, p1, p2, p3 = self.cr, self.uid, self.p1, self.p2, self.p3
        self.assertTrue(self.res_partner.write(cr, uid, [p1,p2,p3], {'phone': '123456'}))

if __name__ == '__main__':
    unittest2.main()
