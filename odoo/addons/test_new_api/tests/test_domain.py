# -*- coding: utf-8 -*-
from itertools import combinations

from odoo.tests import common


class test_domain(common.TransactionCase):

    def setUp(self):
        super(test_domain, self).setUp()
        self.bool = self.env['domain.bool']

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

        model = self.bool
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
