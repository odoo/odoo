# -*- coding: utf-8 -*-
from itertools import combinations

from odoo import Command
from odoo.tests import common


class TestDomain(common.TransactionCase):

    def test_00_test_bool_undefined(self):
        """
        Check that undefined/empty values in database is equal to False and different of True

        """

        # Add a new boolean column after that some rows/tuples has been added (with data)
        # Existing rows/tuples will be undefined/empty
        self.env['ir.model.fields'].create({
            'name': 'x_bool_new_undefined',
            'model_id': self.env.ref('test_new_api.model_domain_bool').id,
            'field_description': 'A new boolean column',
            'ttype': 'boolean'
        })

        self.env.ref('test_new_api.bool_3').write({'x_bool_new_undefined': True})
        self.env.ref('test_new_api.bool_4').write({'x_bool_new_undefined': False})

        model = self.env['domain.bool']
        all_bool = model.search([])
        for f in ['bool_true', 'bool_false', 'bool_undefined', 'x_bool_new_undefined']:
            eq_1 = model.search([(f, '=', False)])
            neq_1 = model.search([(f, '!=', True)])
            self.assertEqual(eq_1, neq_1, '`= False` (%s) <> `!= True` (%s) ' % (len(eq_1), len(neq_1)))

            eq_2 = model.search([(f, '=', True)])
            neq_2 = model.search([(f, '!=', False)])
            self.assertEqual(eq_2, neq_2, '`= True` (%s) <> `!= False` (%s) ' % (len(eq_2), len(neq_2)))

            self.assertEqual(eq_1+eq_2, all_bool, 'True + False != all')
            self.assertEqual(neq_1+neq_2, all_bool, 'not True + not False != all')

    def test_empty_char(self):
        EmptyChar = self.env['test_new_api.empty_char']
        EmptyChar.create([
            {'name': 'name'},
            {'name': ''},
            {'name': False},
        ])

        self.assertListEqual(EmptyChar.search([('name', '=', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(EmptyChar.search([('name', '!=', 'name')]).mapped('name'), ['', False])
        self.assertListEqual(EmptyChar.search([('name', 'ilike', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(EmptyChar.search([('name', 'not ilike', 'name')]).mapped('name'), ['', False])

        self.assertListEqual(EmptyChar.search([('name', '=', '')]).mapped('name'), [''])
        self.assertListEqual(EmptyChar.search([('name', '!=', '')]).mapped('name'), ['name'])
        self.assertListEqual(EmptyChar.search([('name', 'ilike', '')]).mapped('name'), ['name', '', False])
        self.assertListEqual(EmptyChar.search([('name', 'not ilike', '')]).mapped('name'), [False])

        self.assertListEqual(EmptyChar.search([('name', '=', False)]).mapped('name'), [False])
        self.assertListEqual(EmptyChar.search([('name', '!=', False)]).mapped('name'), ['name', ''])
        self.assertListEqual(EmptyChar.search([('name', 'ilike', False)]).mapped('name'), ['name', '', False])
        self.assertListEqual(EmptyChar.search([('name', 'not ilike', False)]).mapped('name'), [False])

        values = ['name', '', False]
        for length in range(len(values) + 1):
            for subset in combinations(values, length):
                sublist = list(subset)
                self.assertListEqual(EmptyChar.search([('name', 'in', sublist)]).mapped('name'), sublist)
                sublist_remained = [v for v in values if v not in subset]
                self.assertListEqual(EmptyChar.search([('name', 'not in', sublist)]).mapped('name'), sublist_remained)

    def test_empty_translation(self):
        records_en = self.env['test_new_api.indexed_translation'].with_context(lang='en_US').create([
            {'name': 'English'},
            {'name': 'English'},
            {'name': 'English'},
        ])
        self.env['res.lang']._activate_lang('fr_FR')
        records_fr = records_en.with_context(lang='fr_FR')
        records_fr[0].name = 'name'
        records_fr[1].name = ''
        records_fr[2].name = False

        self.assertListEqual(records_fr.search([('name', '=', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(records_fr.search([('name', '!=', 'name')]).mapped('name'), ['', False])
        self.assertListEqual(records_fr.search([('name', 'ilike', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(records_fr.search([('name', 'not ilike', 'name')]).mapped('name'), ['', False])

        self.assertListEqual(records_fr.search([('name', '=', '')]).mapped('name'), [''])
        self.assertListEqual(records_fr.search([('name', '!=', '')]).mapped('name'), ['name'])
        self.assertListEqual(records_fr.search([('name', 'ilike', '')]).mapped('name'), ['name', '', False])
        self.assertListEqual(records_fr.search([('name', 'not ilike', '')]).mapped('name'), [False])

        self.assertListEqual(records_fr.search([('name', '=', False)]).mapped('name'), [False])
        self.assertListEqual(records_fr.search([('name', '!=', False)]).mapped('name'), ['name', ''])
        self.assertListEqual(records_fr.search([('name', 'ilike', False)]).mapped('name'), ['name', '', False])
        self.assertListEqual(records_fr.search([('name', 'not ilike', False)]).mapped('name'), [False])

        values = ['name', '', False]
        for length in range(len(values) + 1):
            for subset in combinations(values, length):
                sublist = list(subset)
                self.assertListEqual(records_fr.search([('name', 'in', sublist)]).mapped('name'), sublist)
                sublist_remained = [v for v in values if v not in subset]
                self.assertListEqual(records_fr.search([('name', 'not in', sublist)]).mapped('name'), sublist_remained)

    def test_anys_many2one(self):
        Parent = self.env['test_new_api.any.parent']
        Child = self.env['test_new_api.any.child']

        parent_1, parent_2 = Parent.create([
            {
                'name': 'Jean',
                'child_ids': [
                    Command.create({'quantity': 1}),
                    Command.create({'quantity': 10}),
                ],
            },
            {
                'name': 'Clude',
                'child_ids': [
                    Command.create({'quantity': 2}),
                    Command.create({'quantity': 20}),
                ],
            },
        ])
        # Link parent_1.child_1 to parent_1.child_2
        parent_1.child_ids[0].link_sibling_id = parent_1.child_ids[1]
        # Link parent_2.child_2 to parent_2.child_1
        parent_2.child_ids[1].link_sibling_id = parent_2.child_ids[0]

        # Check any/not any traversing normal Many2one
        res_search = Child.search([('link_sibling_id', 'any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[0])

        res_search = Child.search([('link_sibling_id', 'not any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[1] + parent_2.child_ids)

        # Check any/not any traversing auto_join Many2one
        self.assertFalse(Child._fields['link_sibling_id'].auto_join)
        self.patch(Child._fields['link_sibling_id'], 'auto_join', True)
        self.assertTrue(Child._fields['link_sibling_id'].auto_join)

        res_search = Child.search([('link_sibling_id', 'any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[0])

        res_search = Child.search([('link_sibling_id', 'not any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[1] + parent_2.child_ids)

        # Check any/not any traversing delegate Many2one
        res_search = Child.search([('parent_id', 'any', [('name', '=', 'Jean')])])
        self.assertEqual(res_search, parent_1.child_ids)

        res_search = Child.search([('parent_id', 'not any', [('name', '=', 'Jean')])])
        self.assertEqual(res_search, parent_2.child_ids)

    def test_anys_one2many(self):
        Parent = self.env['test_new_api.any.parent']

        parent_1, parent_2, parent_3 = Parent.create([
            {
                'child_ids': [
                    Command.create({'quantity': 1}),
                    Command.create({'quantity': 10}),
                ],
            },
            {
                'child_ids': [
                    Command.create({'quantity': 2}),
                    Command.create({'quantity': 20}),
                ],
            },
            {},
        ])

        # Check any/not any traversing normal one2many
        res_search = Parent.search([('child_ids', 'any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_1)

        res_search = Parent.search([('child_ids', 'not any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_2 + parent_3)

        # Check any/not any traversing auto_join Many2one
        self.assertFalse(Parent._fields['child_ids'].auto_join)
        self.patch(Parent._fields['child_ids'], 'auto_join', True)
        self.assertTrue(Parent._fields['child_ids'].auto_join)

        res_search = Parent.search([('child_ids', 'any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_1)

        res_search = Parent.search([('child_ids', 'not any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_2 + parent_3)

    def test_anys_many2many(self):
        # auto_join + without
        Child = self.env['test_new_api.any.child']

        child_1, child_2, child_3 = Child.create([
            {
                'tag_ids': [
                    Command.create({'name': 'Urgent'}),
                    Command.create({'name': 'Important'}),
                ],
            },
            {
                'tag_ids': [
                    Command.create({'name': 'Other'}),
                ],
            },
            {},
        ])

        # Check any/not any traversing normal Many2Many
        res_search = Child.search([('tag_ids', 'any', [('name', '=', 'Urgent')])])
        self.assertEqual(res_search, child_1)

        res_search = Child.search([('tag_ids', 'not any', [('name', '=', 'Urgent')])])
        self.assertEqual(res_search, child_2 + child_3)
