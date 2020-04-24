# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, BaseCase
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval, const_eval, expr_eval


class TestSafeEval(BaseCase):
    def test_const(self):
        # NB: True and False are names in Python 2 not consts
        expected = (1, {"a": {2.5}}, [None, u"foo"])
        actual = const_eval('(1, {"a": {2.5}}, [None, u"foo"])')
        self.assertEqual(actual, expected)

    def test_expr(self):
        # NB: True and False are names in Python 2 not consts
        expected = 3 * 4
        actual = expr_eval('3 * 4')
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
        """ Try forbidden expressions in safe_eval to verify they are not allowed"""
        # no forbidden builtin expression
        with self.assertRaises(ValueError):
            safe_eval('open("/etc/passwd","r")')

        # no forbidden opcodes
        with self.assertRaises(ValueError):
            safe_eval("import odoo", mode="exec")

        # no dunder
        with self.assertRaises(NameError):
            safe_eval("self.__name__", {'self': self}, mode="exec")


# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
    ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@CHIRURGIENS-dentistes.fr'),
    ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
]


class TestBase(TransactionCase):

    def _check_find_or_create(self, test_string, expected_name, expected_email, check_partner=False, should_create=False):
        partner = self.env['res.partner'].find_or_create(test_string)
        if should_create and check_partner:
            self.assertTrue(partner.id > check_partner.id, 'find_or_create failed - should have found existing')
        elif check_partner:
            self.assertEqual(partner, check_partner, 'find_or_create failed - should have found existing')
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or '', expected_email)
        return partner

    def test_00_res_partner_name_create(self):
        res_partner = self.env['res.partner']
        parse = res_partner._parse_partner_name
        for text, name, mail in SAMPLES:
            self.assertEqual((name, mail.lower()), parse(text))
            partner_id, dummy = res_partner.name_create(text)
            partner = res_partner.browse(partner_id)
            self.assertEqual(name or mail.lower(), partner.name)
            self.assertEqual(mail.lower() or False, partner.email)

        # name_create supports default_email fallback
        partner = self.env['res.partner'].browse(
            self.env['res.partner'].with_context(
                default_email='John.Wick@example.com'
            ).name_create('"Raoulette Vachette" <Raoul@Grosbedon.fr>')[0]
        )
        self.assertEqual(partner.name, 'Raoulette Vachette')
        self.assertEqual(partner.email, 'raoul@grosbedon.fr')

        partner = self.env['res.partner'].browse(
            self.env['res.partner'].with_context(
                default_email='John.Wick@example.com'
            ).name_create('Raoulette Vachette')[0]
        )
        self.assertEqual(partner.name, 'Raoulette Vachette')
        self.assertEqual(partner.email, 'John.Wick@example.com')

    def test_10_res_partner_find_or_create(self):
        res_partner = self.env['res.partner']

        partner = res_partner.browse(res_partner.name_create(SAMPLES[0][0])[0])
        self._check_find_or_create(
            SAMPLES[0][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        partner_2 = res_partner.browse(res_partner.name_create('sarah.john@connor.com')[0])
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

        new3 = self._check_find_or_create(
            SAMPLES[3][0], SAMPLES[3][1], SAMPLES[3][2],
            check_partner=new2, should_create=True
        )

        new4 = self._check_find_or_create(
            SAMPLES[4][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        new5 = self._check_find_or_create(
            SAMPLES[5][0], SAMPLES[5][1], SAMPLES[5][2],
            check_partner=new4, should_create=True
        )

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

    def test_commercial_partner_nullcompany(self):
        """ The commercial partner is the first/nearest ancestor-or-self which
        is a company or doesn't have a parent
        """
        P = self.env['res.partner']
        p0 = P.create({'name': '0', 'email': '0'})
        self.assertEqual(p0.commercial_partner_id, p0, "partner without a parent is their own commercial partner")

        p1 = P.create({'name': '1', 'email': '1', 'parent_id': p0.id})
        self.assertEqual(p1.commercial_partner_id, p0, "partner's parent is their commercial partner")
        p12 = P.create({'name': '12', 'email': '12', 'parent_id': p1.id})
        self.assertEqual(p12.commercial_partner_id, p0, "partner's GP is their commercial partner")

        p2 = P.create({'name': '2', 'email': '2', 'parent_id': p0.id, 'is_company': True})
        self.assertEqual(p2.commercial_partner_id, p2, "partner flagged as company is their own commercial partner")
        p21 = P.create({'name': '21', 'email': '21', 'parent_id': p2.id})
        self.assertEqual(p21.commercial_partner_id, p2, "commercial partner is closest ancestor with themselves as commercial partner")

        p3 = P.create({'name': '3', 'email': '3', 'is_company': True})
        self.assertEqual(p3.commercial_partner_id, p3, "being both parent-less and company should be the same as either")

        notcompanies = p0 | p1 | p12 | p21
        self.env.cr.execute('update res_partner set is_company=null where id = any(%s)', [notcompanies.ids])
        for parent in notcompanies:
            p = P.create({
                'name': parent.name + '_sub',
                'email': parent.email + '_sub',
                'parent_id': parent.id,
            })
            self.assertEqual(
                p.commercial_partner_id,
                parent.commercial_partner_id,
                "check that is_company=null is properly handled when looking for ancestor"
            )

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


class TestUsers(TransactionCase):
    def test_superuser(self):
        """ The superuser is inactive and must remain as such. """
        user = self.env['res.users'].browse(SUPERUSER_ID)
        self.assertFalse(user.active)
        with self.assertRaises(UserError):
            user.write({'active': True})
