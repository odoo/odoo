# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import unittest

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval, const_eval


@tagged('standard', 'at_install')
class TestSafeEval(unittest.TestCase):
    def test_const(self):
        # NB: True and False are names in Python 2 not consts
        expected = (1, {"a": {2.5}}, [None, u"foo"])
        actual = const_eval('(1, {"a": {2.5}}, [None, u"foo"])')
        self.assertEqual(actual, expected)

    def test_01_safe_eval(self):
        """ Try a few common expressions to verify they work with safe_eval """
        expected = (1, {"a": 9 * 2}, (True, False, None))
        actual = safe_eval('(1, {"a": 9 * 2}, (True, False, None))')
        self.assertEqual(actual, expected, "Simple python expressions are not working with safe_eval")

    def test_02_literal_eval(self):
        """ Try simple literal definition to verify it works with literal_eval """
        expected = (1, {"a": 9}, (True, False, None))
        actual = ast.literal_eval('(1, {"a": 9}, (True, False, None))')
        self.assertEqual(actual, expected, "Simple python expressions are not working with literal_eval")

    def test_03_literal_eval_arithmetic(self):
        """ Try arithmetic expression in literal_eval to verify it does not work """
        with self.assertRaises(ValueError):
           ast.literal_eval('(1, {"a": 2*9}, (True, False, None))')

    def test_04_literal_eval_forbidden(self):
        """ Try forbidden expressions in literal_eval to verify they are not allowed """
        with self.assertRaises(ValueError):
           ast.literal_eval('{"a": True.__class__}')

    @mute_logger('odoo.tools.safe_eval')
    def test_05_safe_eval_forbiddon(self):
        """ Try forbidden expressions in safe_eval to verify they are not allowed (open) """
        with self.assertRaises(ValueError):
            safe_eval('open("/etc/passwd","r")')


# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
]

class TestBase(TransactionCase):

    def test_00_res_partner_name_create(self):
        res_partner = self.env['res.partner']
        parse = res_partner._parse_partner_name
        for text, name, mail in SAMPLES:
            self.assertEqual((name, mail), parse(text), 'Partner name parsing failed')
            partner_id, dummy = res_partner.name_create(text)
            partner = res_partner.browse(partner_id)
            self.assertEqual(name or mail, partner.name, 'Partner name incorrect')
            self.assertEqual(mail or False, partner.email, 'Partner email incorrect')

    def test_10_res_partner_find_or_create(self):
        res_partner = self.env['res.partner']
        email = SAMPLES[0][0]
        partner_id, dummy = res_partner.name_create(email)
        found_id = res_partner.find_or_create(email)
        self.assertEqual(partner_id, found_id, 'find_or_create failed')
        partner_id2, dummy2 = res_partner.name_create('sarah.john@connor.com')
        found_id2 = res_partner.find_or_create('john@connor.com')
        self.assertNotEqual(partner_id2, found_id2, 'john@connor.com match sarah.john@connor.com')
        new_id = res_partner.find_or_create(SAMPLES[1][0])
        self.assertTrue(new_id > partner_id, 'find_or_create failed - should have created new one')
        new_id2 = res_partner.find_or_create(SAMPLES[2][0])
        self.assertTrue(new_id2 > new_id, 'find_or_create failed - should have created new one again')

    def test_15_res_partner_name_search(self):
        res_partner = self.env['res.partner']
        DATA = [
            ('"A Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr>', False),
            ('B Raoul chirurgiens-dentistes.fr', True),
            ("C Raoul O'hara  <!@historicalsociety.museum>", True),
            ('ryu+giga-Sushi@aizubange.fukushima.jp', True),
        ]
        for name, active in DATA:
            partner_id, dummy = res_partner.with_context(default_active=active).name_create(name)
        partners = res_partner.name_search('Raoul')
        self.assertEqual(len(partners), 2, 'Incorrect search number result for name_search')
        partners = res_partner.name_search('Raoul', limit=1)
        self.assertEqual(len(partners), 1, 'Incorrect search number result for name_search with a limit')
        self.assertEqual(partners[0][1], 'B Raoul chirurgiens-dentistes.fr', 'Incorrect partner returned, should be the first active')

    def test_20_res_partner_address_sync(self):
        res_partner = self.env['res.partner']
        ghoststep = res_partner.create({
            'name': 'GhostStep',
            'is_company': True,
            'street': 'Main Street, 10',
            'phone': '123456789',
            'email': 'info@ghoststep.com',
            'vat': 'BE0477472701',
            'type': 'contact',
        })
        p1 = res_partner.browse(res_partner.name_create('Denis Bladesmith <denis.bladesmith@ghoststep.com>')[0])
        self.assertEqual(p1.type, 'contact', 'Default type must be "contact"')
        p1phone = '123456789#34'
        p1.write({'phone': p1phone,
                  'parent_id': ghoststep.id})
        self.assertEqual(p1.street, ghoststep.street, 'Address fields must be synced')
        self.assertEqual(p1.phone, p1phone, 'Phone should be preserved after address sync')
        self.assertEqual(p1.type, 'contact', 'Type should be preserved after address sync')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        # turn off sync
        p1street = 'Different street, 42'
        p1.write({'street': p1street,
                  'type': 'invoice'})
        self.assertEqual(p1.street, p1street, 'Address fields must not be synced after turning sync off')
        self.assertNotEqual(ghoststep.street, p1street, 'Parent address must never be touched')

        # turn on sync again       
        p1.write({'type': 'contact'})
        self.assertEqual(p1.street, ghoststep.street, 'Address fields must be synced again')
        self.assertEqual(p1.phone, p1phone, 'Phone should be preserved after address sync')
        self.assertEqual(p1.type, 'contact', 'Type should be preserved after address sync')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        # Modify parent, sync to children
        ghoststreet = 'South Street, 25'
        ghoststep.write({'street': ghoststreet})
        self.assertEqual(p1.street, ghoststreet, 'Address fields must be synced automatically')
        self.assertEqual(p1.phone, p1phone, 'Phone should not be synced')
        self.assertEqual(p1.email, 'denis.bladesmith@ghoststep.com', 'Email should be preserved after sync')

        p1street = 'My Street, 11'
        p1.write({'street': p1street})
        self.assertEqual(ghoststep.street, ghoststreet, 'Touching contact should never alter parent')

    def test_30_res_partner_first_contact_sync(self):
        """ Test initial creation of company/contact pair where contact address gets copied to
        company """
        res_partner = self.env['res.partner']
        ironshield = res_partner.browse(res_partner.name_create('IronShield')[0])
        self.assertFalse(ironshield.is_company, 'Partners are not companies by default')
        self.assertEqual(ironshield.type, 'contact', 'Default type must be "contact"')
        ironshield.write({'type': 'contact'})

        p1 = res_partner.create({
            'name': 'Isen Hardearth',
            'street': 'Strongarm Avenue, 12',
            'parent_id': ironshield.id,
        })
        self.assertEquals(p1.type, 'contact', 'Default type must be "contact", not the copied parent type')
        self.assertEqual(ironshield.street, p1.street, 'Address fields should be copied to company')

    def test_40_res_partner_address_get(self):
        """ Test address_get address resolution mechanism: it should first go down through descendants,
        stopping when encountering another is_copmany entity, then go up, stopping again at the first
        is_company entity or the root ancestor and if nothing matches, it should use the provided partner
        itself """
        res_partner = self.env['res.partner']
        elmtree = res_partner.browse(res_partner.name_create('Elmtree')[0])
        branch1 = res_partner.create({'name': 'Branch 1',
                                      'parent_id': elmtree.id,
                                      'is_company': True})
        leaf10 = res_partner.create({'name': 'Leaf 10',
                                     'parent_id': branch1.id,
                                     'type': 'invoice'})
        branch11 = res_partner.create({'name': 'Branch 11',
                                       'parent_id': branch1.id,
                                       'type': 'other'})
        leaf111 = res_partner.create({'name': 'Leaf 111',
                                      'parent_id': branch11.id,
                                      'type': 'delivery'})
        branch11.write({'is_company': False})  # force is_company after creating 1rst child
        branch2 = res_partner.create({'name': 'Branch 2',
                                      'parent_id': elmtree.id,
                                      'is_company': True})
        leaf21 = res_partner.create({'name': 'Leaf 21',
                                     'parent_id': branch2.id,
                                     'type': 'delivery'})
        leaf22 = res_partner.create({'name': 'Leaf 22',
                                     'parent_id': branch2.id})
        leaf23 = res_partner.create({'name': 'Leaf 23',
                                     'parent_id': branch2.id,
                                     'type': 'contact'})

        # go up, stop at branch1
        self.assertEqual(leaf111.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')
        self.assertEqual(branch11.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')

        # go down, stop at at all child companies
        self.assertEqual(elmtree.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': elmtree.id,
                          'invoice': elmtree.id,
                          'contact': elmtree.id,
                          'other': elmtree.id}, 'Invalid address resolution')

        # go down through children
        self.assertEqual(branch1.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf111.id,
                          'invoice': leaf10.id,
                          'contact': branch1.id,
                          'other': branch11.id}, 'Invalid address resolution')

        self.assertEqual(branch2.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': branch2.id,
                          'contact': branch2.id,
                          'other': branch2.id}, 'Invalid address resolution. Company is the first encountered contact, therefore default for unfound addresses.')

        # go up then down through siblings
        self.assertEqual(leaf21.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': branch2.id,
                          'contact': branch2.id,
                          'other': branch2.id}, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(leaf22.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': leaf22.id,
                          'contact': leaf22.id,
                          'other': leaf22.id}, 'Invalid address resolution, should scan commercial entity ancestor and its descendants')
        self.assertEqual(leaf23.address_get(['delivery', 'invoice', 'contact', 'other']),
                         {'delivery': leaf21.id,
                          'invoice': leaf23.id,
                          'contact': leaf23.id,
                          'other': leaf23.id}, 'Invalid address resolution, `default` should only override if no partner with specific type exists')

        # empty adr_pref means only 'contact'
        self.assertEqual(elmtree.address_get([]),
                        {'contact': elmtree.id}, 'Invalid address resolution, no contact means commercial entity ancestor')
        self.assertEqual(leaf111.address_get([]),
                        {'contact': branch1.id}, 'Invalid address resolution, no contact means finding contact in ancestors')
        branch11.write({'type': 'contact'})
        self.assertEqual(leaf111.address_get([]),
                        {'contact': branch11.id}, 'Invalid address resolution, branch11 should now be contact')

    def test_50_res_partner_commercial_sync(self):
        res_partner = self.env['res.partner']
        p0 = res_partner.create({'name': 'Sigurd Sunknife',
                                 'email': 'ssunknife@gmail.com'})
        sunhelm = res_partner.create({'name': 'Sunhelm',
                                      'is_company': True,
                                      'street': 'Rainbow Street, 13',
                                      'phone': '1122334455',
                                      'email': 'info@sunhelm.com',
                                      'vat': 'BE0477472701',
                                      'child_ids': [(4, p0.id),
                                                    (0, 0, {'name': 'Alrik Greenthorn',
                                                            'email': 'agr@sunhelm.com'})]})
        p1 = res_partner.create({'name': 'Otto Blackwood',
                                 'email': 'otto.blackwood@sunhelm.com',
                                 'parent_id': sunhelm.id})
        p11 = res_partner.create({'name': 'Gini Graywool',
                                  'email': 'ggr@sunhelm.com',
                                  'parent_id': p1.id})
        p2 = res_partner.search([('email', '=', 'agr@sunhelm.com')], limit=1)
        sunhelm.write({'child_ids': [(0, 0, {'name': 'Ulrik Greenthorn',
                                             'email': 'ugr@sunhelm.com'})]})
        p3 = res_partner.search([('email', '=', 'ugr@sunhelm.com')], limit=1)

        for p in (p0, p1, p11, p2, p3):
            self.assertEquals(p.commercial_partner_id, sunhelm, 'Incorrect commercial entity resolution')
            self.assertEquals(p.vat, sunhelm.vat, 'Commercial fields must be automatically synced')
        sunhelmvat = 'BE0123456789'
        sunhelm.write({'vat': sunhelmvat})
        for p in (p0, p1, p11, p2, p3):
            self.assertEquals(p.vat, sunhelmvat, 'Commercial fields must be automatically and recursively synced')

        p1vat = 'BE0987654321'
        p1.write({'vat': p1vat})
        for p in (sunhelm, p0, p11, p2, p3):
            self.assertEquals(p.vat, sunhelmvat, 'Sync to children should only work downstream and on commercial entities')

        # promote p1 to commercial entity
        p1.write({'parent_id': sunhelm.id,
                  'is_company': True,
                  'name': 'Sunhelm Subsidiary'})
        self.assertEquals(p1.vat, p1vat, 'Setting is_company should stop auto-sync of commercial fields')
        self.assertEquals(p1.commercial_partner_id, p1, 'Incorrect commercial entity resolution after setting is_company')

        # writing on parent should not touch child commercial entities
        sunhelmvat2 = 'BE0112233445'
        sunhelm.write({'vat': sunhelmvat2})
        self.assertEquals(p1.vat, p1vat, 'Setting is_company should stop auto-sync of commercial fields')
        self.assertEquals(p0.vat, sunhelmvat2, 'Commercial fields must be automatically synced')

    def test_60_read_group(self):
        title_sir = self.env['res.partner.title'].create({'name': 'Sir...'})
        title_lady = self.env['res.partner.title'].create({'name': 'Lady...'})
        test_users = [
            {'name': 'Alice', 'login': 'alice', 'color': 1, 'function': 'Friend', 'date': '2015-03-28', 'title': title_lady.id},
            {'name': 'Alice', 'login': 'alice2', 'color': 0, 'function': 'Friend',  'date': '2015-01-28', 'title': title_lady.id},
            {'name': 'Bob', 'login': 'bob', 'color': 2, 'function': 'Friend', 'date': '2015-03-02', 'title': title_sir.id},
            {'name': 'Eve', 'login': 'eve', 'color': 3, 'function': 'Eavesdropper', 'date': '2015-03-20', 'title': title_lady.id},
            {'name': 'Nab', 'login': 'nab', 'color': -3, 'function': '5$ Wrench', 'date': '2014-09-10', 'title': title_sir.id},
            {'name': 'Nab', 'login': 'nab-she', 'color': 6, 'function': '5$ Wrench', 'date': '2014-01-02', 'title': title_lady.id},
        ]
        res_users = self.env['res.users']
        user_ids = [res_users.create(vals).id for vals in test_users]
        domain = [('id', 'in', user_ids)]

        # group on local char field without domain and without active_test (-> empty WHERE clause)
        groups_data = res_users.with_context(active_test=False).read_group([], fields=['login'], groupby=['login'], orderby='login DESC')
        self.assertGreater(len(groups_data), 6, "Incorrect number of results when grouping on a field")

        # group on local char field with limit
        groups_data = res_users.read_group(domain, fields=['login'], groupby=['login'], orderby='login DESC', limit=3, offset=3)
        self.assertEqual(len(groups_data), 3, "Incorrect number of results when grouping on a field with limit")
        self.assertEqual(['bob', 'alice2', 'alice'], [g['login'] for g in groups_data], 'Result mismatch')

        # group on inherited char field, aggregate on int field (second groupby ignored on purpose)
        groups_data = res_users.read_group(domain, fields=['name', 'color', 'function'], groupby=['function', 'login'])
        self.assertEqual(len(groups_data), 3, "Incorrect number of results when grouping on a field")
        self.assertEqual(['5$ Wrench', 'Eavesdropper', 'Friend'], [g['function'] for g in groups_data], 'incorrect read_group order')
        for group_data in groups_data:
            self.assertIn('color', group_data, "Aggregated data for the column 'color' is not present in read_group return values")
            self.assertEqual(group_data['color'], 3, "Incorrect sum for aggregated data for the column 'color'")

        # group on inherited char field, reverse order
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby='name', orderby='name DESC')
        self.assertEqual(['Nab', 'Eve', 'Bob', 'Alice'], [g['name'] for g in groups_data], 'Incorrect ordering of the list')

        # group on int field, default ordering
        groups_data = res_users.read_group(domain, fields=['color'], groupby='color')
        self.assertEqual([-3, 0, 1, 2, 3, 6], [g['color'] for g in groups_data], 'Incorrect ordering of the list')

        # multi group, second level is int field, should still be summed in first level grouping
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby=['name', 'color'], orderby='name DESC')
        self.assertEqual(['Nab', 'Eve', 'Bob', 'Alice'], [g['name'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([3, 3, 2, 1], [g['color'] for g in groups_data], 'Incorrect ordering of the list')

        # group on inherited char field, multiple orders with directions
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby='name', orderby='color DESC, name')
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual(['Eve', 'Nab', 'Bob', 'Alice'], [g['name'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([1, 2, 1, 2], [g['name_count'] for g in groups_data], 'Incorrect number of results')

        # group on inherited date column (res_partner.date) -> Year-Month, default ordering
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'date'], groupby=['date'])
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual(['January 2014', 'September 2014', 'January 2015', 'March 2015'], [g['date'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([1, 1, 1, 3], [g['date_count'] for g in groups_data], 'Incorrect number of results')

        # group on inherited date column (res_partner.date) -> Year-Month, custom order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'date'], groupby=['date'], orderby='date DESC')
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual(['March 2015', 'January 2015', 'September 2014', 'January 2014'], [g['date'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([3, 1, 1, 1], [g['date_count'] for g in groups_data], 'Incorrect number of results')

        # group on inherited many2one (res_partner.title), default order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'title'], groupby=['title'])
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([(title_lady.id, 'Lady...'), (title_sir.id, 'Sir...')], [g['title'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([4, 2], [g['title_count'] for g in groups_data], 'Incorrect number of results')
        self.assertEqual([10, -1], [g['color'] for g in groups_data], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.title), reversed natural order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'title'], groupby=['title'], orderby="title desc")
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([(title_sir.id, 'Sir...'), (title_lady.id, 'Lady...')], [g['title'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([2, 4], [g['title_count'] for g in groups_data], 'Incorrect number of results')
        self.assertEqual([-1, 10], [g['color'] for g in groups_data], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.title), multiple orders with m2o in second position
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'title'], groupby=['title'], orderby="color desc, title desc")
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([(title_lady.id, 'Lady...'), (title_sir.id, 'Sir...')], [g['title'] for g in groups_data], 'Incorrect ordering of the result')
        self.assertEqual([4, 2], [g['title_count'] for g in groups_data], 'Incorrect number of results')
        self.assertEqual([10, -1], [g['color'] for g in groups_data], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.title), ordered by other inherited field (color)
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'title'], groupby=['title'], orderby='color')
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([(title_sir.id, 'Sir...'), (title_lady.id, 'Lady...')], [g['title'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([2, 4], [g['title_count'] for g in groups_data], 'Incorrect number of results')
        self.assertEqual([-1, 10], [g['color'] for g in groups_data], 'Incorrect aggregation of int column')

    def test_70_archive_internal_partners(self):
        test_partner = self.env['res.partner'].create({'name':'test partner'})
        test_user = self.env['res.users'].create({
                                'login': 'test@odoo.com',
                                'partner_id': test_partner.id,
                                })
        # Cannot archive the partner
        with self.assertRaises(ValidationError):
            test_partner.toggle_active()

        # Can archive the user but the partner stays active
        test_user.toggle_active()
        self.assertTrue(test_partner.active, 'Parter related to user should remain active')

        # Now we can archive the partner
        test_partner.toggle_active()

        # Activate the user should reactivate the partner
        test_user.toggle_active()
        self.assertTrue(test_partner.active, 'Activating user must active related partner')


class TestPartnerRecursion(TransactionCase):

    def setUp(self):
        super(TestPartnerRecursion,self).setUp()
        res_partner = self.env['res.partner']
        self.p1 = res_partner.browse(res_partner.name_create('Elmtree')[0])
        self.p2 = res_partner.create({'name': 'Elmtree Child 1', 'parent_id': self.p1.id})
        self.p3 = res_partner.create({'name': 'Elmtree Grand-Child 1.1', 'parent_id': self.p2.id})

    def test_100_res_partner_recursion(self):
        self.assertTrue(self.p3._check_recursion())
        self.assertTrue((self.p1 + self.p2 + self.p3)._check_recursion())

    # split 101, 102, 103 tests to force SQL rollback between them

    def test_101_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p1.write({'parent_id': self.p3.id})

    def test_102_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p2.write({'parent_id': self.p3.id})

    def test_103_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p3.write({'parent_id': self.p3.id})

    def test_104_res_partner_recursion_indirect_cycle(self):
        """ Indirect hacky write to create cycle in children """
        p3b = self.p1.create({'name': 'Elmtree Grand-Child 1.2', 'parent_id': self.p2.id})
        with self.assertRaises(ValidationError):
            self.p2.write({'child_ids': [(1, self.p3.id, {'parent_id': p3b.id}),
                                         (1, p3b.id, {'parent_id': self.p3.id})]})

    def test_110_res_partner_recursion_multi_update(self):
        """ multi-write on several partners in same hierarchy must not trigger a false cycle detection """
        ps = self.p1 + self.p2 + self.p3
        self.assertTrue(ps.write({'phone': '123456'}))


class TestParentStore(TransactionCase):
    """ Verify that parent_store computation is done right """

    def setUp(self):
        super(TestParentStore, self).setUp()

        # force res_partner_category.copy() to copy children
        category = self.env['res.partner.category']
        self.patch(category._fields['child_ids'], 'copy', True)

        # setup categories
        self.root = category.create({'name': 'Root category'})
        self.cat0 = category.create({'name': 'Parent category', 'parent_id': self.root.id})
        self.cat1 = category.create({'name': 'Child 1', 'parent_id': self.cat0.id})
        self.cat2 = category.create({'name': 'Child 2', 'parent_id': self.cat0.id})
        self.cat21 = category.create({'name': 'Child 2-1', 'parent_id': self.cat2.id})

    def test_duplicate_parent(self):
        """ Duplicate the parent category and verify that the children have been duplicated too """
        new_cat0 = self.cat0.copy()
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_01(self):
        """ Duplicate the children then reassign them to the new parent (1st method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        (new_cat1 + new_cat2).write({'parent_id': new_cat0.id})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_02(self):
        """ Duplicate the children then reassign them to the new parent (2nd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': [(6, 0, (new_cat1 + new_cat2).ids)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_03(self):
        """ Duplicate the children then reassign them to the new parent (3rd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        new_cat0.write({'child_ids': [(4, new_cat1.id), (4, new_cat2.id)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")


class TestGroups(TransactionCase):

    def test_res_groups_fullname_search(self):
        all_groups = self.env['res.groups'].search([])

        groups = all_groups.search([('full_name', 'like', '%Sale%')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Sale' in g.full_name],
                              "did not match search for 'Sale'")

        groups = all_groups.search([('full_name', 'like', '%Technical%')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Technical' in g.full_name],
                              "did not match search for 'Technical'")

        groups = all_groups.search([('full_name', 'like', '%Sales /%')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Sales /' in g.full_name],
                              "did not match search for 'Sales /'")

        groups = all_groups.search([('full_name', 'in', ['Administration / Access Rights','Contact Creation'])])
        self.assertTrue(groups, "did not match search for 'Administration / Access Rights' and 'Contact Creation'")

    def test_res_group_recursion(self):
        # four groups with no cycle, check them all together
        a = self.env['res.groups'].create({'name': 'A'})
        b = self.env['res.groups'].create({'name': 'B'})
        c = self.env['res.groups'].create({'name': 'G', 'implied_ids': [(6, 0, (a + b).ids)]})
        d = self.env['res.groups'].create({'name': 'D', 'implied_ids': [(6, 0, c.ids)]})
        self.assertTrue((a + b + c + d)._check_m2m_recursion('implied_ids'))

        # create a cycle and check
        a.implied_ids = d
        self.assertFalse(a._check_m2m_recursion('implied_ids'))

    def test_res_group_copy(self):
        a = self.env['res.groups'].with_context(lang='en_US').create({'name': 'A'})
        b = a.copy()
        self.assertFalse(a.name == b.name)
