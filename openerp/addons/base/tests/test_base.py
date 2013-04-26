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


    def test_20_res_partner_address_sync(self):
        cr, uid = self.cr, self.uid
        ghoststep = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                             {'name': 'GhostStep',
                                                                              'is_company': True,
                                                                              'street': 'Main Street, 10',
                                                                              'phone': '123456789',
                                                                              'email': 'info@ghoststep.com',
                                                                              'vat': 'BE0477472701',
                                                                              'type': 'default'}))
        p1 = self.res_partner.browse(cr, uid, self.res_partner.name_create(cr, uid, 'Denis Bladesmith <denis.bladesmith@ghoststep.com>')[0])
        self.assertEqual(p1.type, 'contact', 'Default type must be "contact"')
        p1phone = '123456789#34'
        p1.write({'phone': p1phone,
                  'parent_id': ghoststep.id,
                  'use_parent_address': True})
        p1.refresh()
        self.assertEqual(p1.street, ghoststep.street, 'Address fields must be synced')
        self.assertEqual(p1.phone, p1phone, 'Phone should be preserved after address sync')
        self.assertEqual(p1.type, 'contact', 'Type should be preserved after address sync')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        # turn off sync
        p1street = 'Different street, 42'
        p1.write({'street': p1street,
                  'use_parent_address': False})
        p1.refresh(), ghoststep.refresh() 
        self.assertEqual(p1.street, p1street, 'Address fields must not be synced after turning sync off')
        self.assertNotEqual(ghoststep.street, p1street, 'Parent address must never be touched')

        # turn on sync again       
        p1.write({'use_parent_address': True})
        p1.refresh()
        self.assertEqual(p1.street, ghoststep.street, 'Address fields must be synced again')
        self.assertEqual(p1.phone, p1phone, 'Phone should be preserved after address sync')
        self.assertEqual(p1.type, 'contact', 'Type should be preserved after address sync')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        # Modify parent, sync to children
        ghoststreet = 'South Street, 25'
        ghoststep.write({'street': ghoststreet})
        p1.refresh()
        self.assertEqual(p1.street, ghoststreet, 'Address fields must be synced automatically')
        self.assertEqual(p1.phone, p1phone, 'Phone should not be synced')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        p1street = 'My Street, 11'
        p1.write({'street': p1street})
        ghoststep.refresh()
        self.assertEqual(ghoststep.street, ghoststreet, 'Touching contact should never alter parent')


    def test_30_res_partner_first_contact_sync(self):
        """ Test initial creation of company/contact pair where contact address gets copied to
        company """
        cr, uid = self.cr, self.uid
        ironshield = self.res_partner.browse(cr, uid, self.res_partner.name_create(cr, uid, 'IronShield')[0])
        self.assertFalse(ironshield.is_company, 'Partners are not companies by default')
        self.assertFalse(ironshield.use_parent_address, 'use_parent_address defaults to False')
        self.assertEqual(ironshield.type, 'contact', 'Default type must be "contact"')
        ironshield.write({'type': 'default'}) # force default type to double-check sync 
        p1 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                      {'name': 'Isen Hardearth',
                                                                       'street': 'Strongarm Avenue, 12',
                                                                       'parent_id': ironshield.id}))
        self.assertEquals(p1.type, 'contact', 'Default type must be "contact", not the copied parent type')
        ironshield.refresh()
        self.assertEqual(ironshield.street, p1.street, 'Address fields should be copied to company')
        self.assertTrue(ironshield.is_company, 'Company flag should be turned on after first contact creation')

    def test_40_res_partner_address_getc(self):
        """ Test address_get address resolution mechanism: it should first go down through descendants,
        stopping when encountering another is_copmany entity, then go up, stopping again at the first
        is_company entity or the root ancestor and if nothing matches, it should use the provided partner
        itself """
        cr, uid = self.cr, self.uid
        elmtree = self.res_partner.browse(cr, uid, self.res_partner.name_create(cr, uid, 'Elmtree')[0])
        branch1 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Branch 1',
                                                                                     'parent_id': elmtree.id,
                                                                                     'is_company': True}))
        leaf10 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Leaf 10',
                                                                                    'parent_id': branch1.id,
                                                                                    'type': 'invoice'}))
        branch11 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Branch 11',
                                                                                      'parent_id': branch1.id,
                                                                                      'type': 'other'}))
        leaf111 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Leaf 111',
                                                                                    'parent_id': branch11.id,
                                                                                    'type': 'delivery'}))
        branch11.write({'is_company': False}) # force is_company after creating 1rst child
        branch2 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Branch 2',
                                                                                     'parent_id': elmtree.id,
                                                                                     'is_company': True}))
        leaf21 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Leaf 21',
                                                                                    'parent_id': branch2.id,
                                                                                    'type': 'delivery'}))
        leaf22 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Leaf 22',
                                                                                    'parent_id': branch2.id}))
        leaf23 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid, {'name': 'Leaf 23',
                                                                                    'parent_id': branch2.id,
                                                                                    'type': 'default'}))
        # go up, stop at branch1
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf111.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id,
                          'default': leaf111.id}, 'Invalid address resolution')
        self.assertEqual(self.res_partner.address_get(cr, uid, [branch11.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id,
                          'default': branch11.id}, 'Invalid address resolution')

        # go down, stop at at all child companies
        self.assertEqual(self.res_partner.address_get(cr, uid, [elmtree.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': elmtree.id,
                          'invoice': elmtree.id,
                          'contact': elmtree.id,
                          'other': elmtree.id,
                          'default': elmtree.id}, 'Invalid address resolution')

        # go down through children
        self.assertEqual(self.res_partner.address_get(cr, uid, [branch1.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id,
                          'default': branch1.id}, 'Invalid address resolution')
        self.assertEqual(self.res_partner.address_get(cr, uid, [branch2.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': branch2.id,
                          'other': leaf23.id,
                          'default': leaf23.id}, 'Invalid address resolution')

        # go up then down through siblings
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf21.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': branch2.id,
                          'other': leaf23.id,
                          'default': leaf23.id
                          }, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf22.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': leaf22.id,
                          'other': leaf23.id,
                          'default': leaf23.id}, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf23.id], ['delivery', 'invoice', 'contact', 'other', 'default']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': branch2.id,
                          'other': leaf23.id,
                          'default': leaf23.id}, 'Invalid address resolution, `default` should only override if no partner with specific type exists')

        # empty adr_pref means only 'default'
        self.assertEqual(self.res_partner.address_get(cr, uid, [elmtree.id], []),
                        {'default': elmtree.id}, 'Invalid address resolution, no default means commercial entity ancestor')
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf111.id], []),
                        {'default': leaf111.id}, 'Invalid address resolution, no default means contact itself')
        branch11.write({'type': 'default'})
        self.assertEqual(self.res_partner.address_get(cr, uid, [leaf111.id], []),
                        {'default': branch11.id}, 'Invalid address resolution, branch11 should now be default')


    def test_50_res_partner_commercial_sync(self):    
        cr, uid = self.cr, self.uid
        p0 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                      {'name': 'Sigurd Sunknife',
                                                                       'email': 'ssunknife@gmail.com'}))
        sunhelm = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                           {'name': 'Sunhelm',
                                                                            'is_company': True,
                                                                            'street': 'Rainbow Street, 13',
                                                                            'phone': '1122334455',
                                                                            'email': 'info@sunhelm.com',
                                                                            'vat': 'BE0477472701',
                                                                            'child_ids': [(4, p0.id),
                                                                                          (0, 0, {'name': 'Alrik Greenthorn',
                                                                                                  'email': 'agr@sunhelm.com'})],
                                                                            }))
        p1 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                      {'name': 'Otto Blackwood',
                                                                       'email': 'otto.blackwood@sunhelm.com',
                                                                       'parent_id': sunhelm.id}))
        p11 = self.res_partner.browse(cr, uid, self.res_partner.create(cr, uid,
                                                                      {'name': 'Gini Graywool',
                                                                       'email': 'ggr@sunhelm.com',
                                                                       'parent_id': p1.id}))
        p2 = self.res_partner.browse(cr, uid, self.res_partner.search(cr, uid,
                                                                      [('email', '=', 'agr@sunhelm.com')])[0])

        for p in (p0, p1, p11, p2):
            p.refresh()
            self.assertEquals(p.commercial_partner_id, sunhelm, 'Incorrect commercial entity resolution')
            self.assertEquals(p.vat, sunhelm.vat, 'Commercial fields must be automatically synced')
        sunhelmvat = 'BE0123456789'
        sunhelm.write({'vat': sunhelmvat})
        for p in (p0, p1, p11, p2):
            p.refresh()
            self.assertEquals(p.vat, sunhelmvat, 'Commercial fields must be automatically and recursively synced')

        p1vat = 'BE0987654321'
        p1.write({'vat': p1vat})
        for p in (sunhelm, p0, p11, p2):
            p.refresh()
            self.assertEquals(p.vat, sunhelmvat, 'Sync to children should only work downstream and on commercial entities')

        # promote p1 to commercial entity
        vals = p1.onchange_type(is_company=True)['value']
        p1.write(dict(vals, parent_id=sunhelm.id,
                      is_company=True,
                      name='Sunhelm Subsidiary'))
        p1.refresh()
        self.assertEquals(p1.vat, p1vat, 'Setting is_company should stop auto-sync of commercial fields')
        self.assertEquals(p1.commercial_partner_id, p1, 'Incorrect commercial entity resolution after setting is_company')

        # writing on parent should not touch child commercial entities
        sunhelmvat2 = 'BE0112233445'
        sunhelm.write({'vat': sunhelmvat2})
        p1.refresh()
        self.assertEquals(p1.vat, p1vat, 'Setting is_company should stop auto-sync of commercial fields')
        p0.refresh()
        self.assertEquals(p0.vat, sunhelmvat2, 'Commercial fields must be automatically synced')

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
