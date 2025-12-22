from itertools import combinations

from odoo import Command
from odoo.addons.base.tests.test_expression import TransactionExpressionCase
from odoo.tools import SQL


class TestDomain(TransactionExpressionCase):

    def _search(self, model, domain, init_domain=None, test_complement=False):
        # just overwrite the defaults here, because we test complements manually
        return super()._search(model, domain, init_domain, test_complement)

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
            eq_1 = self._search(model, [(f, '=', False)])
            neq_1 = self._search(model, [(f, '!=', True)])
            self.assertEqual(eq_1, neq_1, '`= False` (%s) <> `!= True` (%s) ' % (len(eq_1), len(neq_1)))

            eq_2 = self._search(model, [(f, '=', True)])
            neq_2 = self._search(model, [(f, '!=', False)])
            self.assertEqual(eq_2, neq_2, '`= True` (%s) <> `!= False` (%s) ' % (len(eq_2), len(neq_2)))

            self.assertEqual(eq_1+eq_2, all_bool, 'True + False != all')
            self.assertEqual(neq_1+neq_2, all_bool, 'not True + not False != all')

    def test_empty_int(self):
        EmptyInt = self.env['test_new_api.empty_int']
        records = EmptyInt.create([
            {'number': 42},     # stored as 42
            {'number': 0},      # stored as 0
            {'number': False},  # stored as 0
            {},                 # stored as NULL
        ])
        # check read (NULL is returned as 0)
        self.assertListEqual(records.mapped('number'), [42, 0, 0, 0])

        # check database value
        self.env.flush_all()

        sql = SQL("SELECT number FROM test_new_api_empty_int WHERE id IN %s ORDER BY id", records._ids)
        rows = self.env.execute_query(sql)
        self.assertEqual([row[0] for row in rows], [42, 0, 0, None])

        self.assertListEqual(self._search(EmptyInt, [('number', '=', 42)]).mapped('number'), [42])
        self.assertListEqual(self._search(EmptyInt, [('number', '!=', 42)]).mapped('number'), [0, 0, 0])

        self.assertListEqual(self._search(EmptyInt, [('number', '=', 0)]).mapped('number'), [0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '!=', 0)]).mapped('number'), [42])

        self.assertListEqual(self._search(EmptyInt, [('number', '=', False)]).mapped('number'), [0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '!=', False)]).mapped('number'), [42])

        self.assertListEqual(self._search(EmptyInt, [('number', '<', 1)]).mapped('number'), [0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '>', -1)]).mapped('number'), [42, 0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '<=', 0)]).mapped('number'), [0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '>=', 0)]).mapped('number'), [42, 0, 0, 0])
        self.assertListEqual(self._search(EmptyInt, [('number', '>', 1)]).mapped('number'), [42])
        self.assertListEqual(self._search(EmptyInt, [('number', '<', -1)]).mapped('number'), [])

        # check ('number', 'in', subset) for every subset of {42, 0, False}
        values = [42, 0, False]
        for length in range(len(values) + 1):
            for subset in combinations(values, length):
                self.assertEqual(
                    self._search(EmptyInt, [('number', 'in', list(subset))]),
                    records.filtered(lambda record: record.number in subset),
                    f"Incorrect result for search([('number', 'in', {sorted(subset)})])",
                )
                self.assertEqual(
                    self._search(EmptyInt, [('number', 'not in', list(subset))]),
                    records.filtered(lambda record: record.number not in subset),
                    f"Incorrect result for search([('number', 'not in', {sorted(subset)})])",
                )

    def test_empty_char(self):
        EmptyChar = self.env['test_new_api.empty_char']
        records = EmptyChar.create([
            {'name': 'name'},
            {'name': ''},      # stored as ''
            {'name': False},   # stored as null (explicitly asked)
            {},                # stored as null
        ])
        # check read
        self.assertListEqual(records.mapped('name'), ['name', '', False, False])

        # check database value
        self.env.flush_all()

        sql = SQL("SELECT name FROM test_new_api_empty_char WHERE id IN %s ORDER BY id", records._ids)
        rows = self.env.execute_query(sql)
        self.assertEqual([row[0] for row in rows], ['name', '', None, None])

        self.assertListEqual(self._search(EmptyChar, [('name', '=', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(EmptyChar, [('name', '!=', 'name')]).mapped('name'), ['', False, False])
        self.assertListEqual(self._search(EmptyChar, [('name', 'ilike', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(EmptyChar, [('name', 'not ilike', 'name')]).mapped('name'), ['', False, False])

        self.assertListEqual(self._search(EmptyChar, [('name', '=', '')]).mapped('name'), ['', False, False])
        self.assertListEqual(self._search(EmptyChar, [('name', '!=', '')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(EmptyChar, [('name', 'ilike', '')]).mapped('name'), ['name', '', False, False])
        self.assertListEqual(self._search(EmptyChar, [('name', 'not ilike', '')]).mapped('name'), [])

        self.assertListEqual(self._search(EmptyChar, [('name', '=', False)]).mapped('name'), ['', False, False])
        self.assertListEqual(self._search(EmptyChar, [('name', '!=', False)]).mapped('name'), ['name'])
        self.assertListEqual(self._search(EmptyChar, [('name', 'ilike', False)]).mapped('name'), ['name', '', False, False])
        self.assertListEqual(self._search(EmptyChar, [('name', 'not ilike', False)]).mapped('name'), [])

        values = ['name', '', False]
        for length in range(len(values) + 1):
            for subset in combinations(values, length):
                # check against a subset containg both values for empty strings
                subset_check = set(subset)
                if {False, ""} & subset_check:
                    subset_check |= {False, ""}
                self.assertEqual(
                    self._search(EmptyChar, [('name', 'in', list(subset))]),
                    records.filtered(lambda record: record.name in subset_check),
                    f"Incorrect result for search([('name', 'in', {list(subset)})])",
                )
                self.assertEqual(
                    self._search(EmptyChar, [('name', 'not in', list(subset))]),
                    records.filtered(lambda record: record.name not in subset_check),
                    f"Incorrect result for search([('name', 'not in', {list(subset)})])",
                )

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
        self.assertListEqual(records_en.mapped('name'), ['English', 'English', False])
        self.assertListEqual(records_fr.mapped('name'), ['name', '', False])

        self.assertListEqual(self._search(records_fr, [('name', '=', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(records_fr, [('name', '!=', 'name')]).mapped('name'), ['', False])
        self.assertListEqual(self._search(records_fr, [('name', 'ilike', 'name')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(records_fr, [('name', 'not ilike', 'name')]).mapped('name'), ['', False])

        self.assertListEqual(self._search(records_fr, [('name', '=', '')]).mapped('name'), ['', False])
        self.assertListEqual(self._search(records_fr, [('name', '!=', '')]).mapped('name'), ['name'])
        self.assertListEqual(self._search(records_fr, [('name', 'ilike', '')]).mapped('name'), ['name', '', False])
        self.assertListEqual(self._search(records_fr, [('name', 'not ilike', '')]).mapped('name'), [])

        self.assertListEqual(self._search(records_fr, [('name', '=', False)]).mapped('name'), ['', False])
        self.assertListEqual(self._search(records_fr, [('name', '!=', False)]).mapped('name'), ['name'])
        self.assertListEqual(self._search(records_fr, [('name', 'ilike', False)]).mapped('name'), ['name', '', False])
        self.assertListEqual(self._search(records_fr, [('name', 'not ilike', False)]).mapped('name'), [])

        values = ['name', '', False]
        for length in range(len(values) + 1):
            for subset in combinations(values, length):
                # check against a subset containg both values for empty strings
                subset_check = set(subset)
                if {False, ""} & subset_check:
                    subset_check |= {False, ""}
                self.assertEqual(
                    self._search(records_fr, [('name', 'in', list(subset))]),
                    records_fr.filtered(lambda record: record.name in subset_check),
                    f"Incorrect result for search([('name', 'in', {list(subset)})])",
                )
                self.assertEqual(
                    self._search(records_fr, [('name', 'not in', list(subset))]),
                    records_fr.filtered(lambda record: record.name not in subset_check),
                    f"Incorrect result for search([('name', 'not in', {list(subset)})])",
                )

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
        res_search = self._search(Child, [('link_sibling_id', 'any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[0])

        res_search = self._search(Child, [('link_sibling_id', 'not any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[1] + parent_2.child_ids)

        # Check any/not any traversing auto_join Many2one
        self.assertFalse(Child._fields['link_sibling_id'].auto_join)
        self.patch(Child._fields['link_sibling_id'], 'auto_join', True)
        self.assertTrue(Child._fields['link_sibling_id'].auto_join)

        res_search = self._search(Child, [('link_sibling_id', 'any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[0])

        res_search = self._search(Child, [('link_sibling_id', 'not any', [('quantity', '>', 5)])])
        self.assertEqual(res_search, parent_1.child_ids[1] + parent_2.child_ids)

        # Check any/not any traversing delegate Many2one
        res_search = self._search(Child, [('parent_id', 'any', [('name', '=', 'Jean')])])
        self.assertEqual(res_search, parent_1.child_ids)

        res_search = self._search(Child, [('parent_id', 'not any', [('name', '=', 'Jean')])])
        self.assertEqual(res_search, parent_2.child_ids)

    def test_anys_many2one_implicit(self):
        Parent = self.env['test_new_api.any.parent']

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

        res_search = self._search(Parent, [('child_ids.quantity', '=', 1)])
        self.assertEqual(res_search, parent_1)

        res_search = self._search(Parent, [('child_ids.quantity', '>', 15)])
        self.assertEqual(res_search, parent_2)

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
        res_search = self._search(Parent, [('child_ids', 'any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_1)

        res_search = self._search(Parent, [('child_ids', 'not any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_2 + parent_3)

        # Check any/not any traversing auto_join Many2one
        self.assertFalse(Parent._fields['child_ids'].auto_join)
        self.patch(Parent._fields['child_ids'], 'auto_join', True)
        self.assertTrue(Parent._fields['child_ids'].auto_join)

        res_search = self._search(Parent, [('child_ids', 'any', [('quantity', '=', 1)])])
        self.assertEqual(res_search, parent_1)

        res_search = self._search(Parent, [('child_ids', 'not any', [('quantity', '=', 1)])])
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
        res_search = self._search(Child, [('tag_ids', 'any', [('name', '=', 'Urgent')])])
        self.assertEqual(res_search, child_1)

        res_search = self._search(Child, [('tag_ids', 'not any', [('name', '=', 'Urgent')])])
        self.assertEqual(res_search, child_2 + child_3)


class TestDomainComplement(TransactionExpressionCase):

    def test_inequalities_int(self):
        Model = self.env['test_new_api.empty_int']
        Model.create([{}])
        Model.create([{'number': n} for n in range(-5, 6)])
        self._search(Model, [('number', '>', 2)])
        self._search(Model, [('number', '>', -2)])
        self._search(Model, [('number', '<', 1)])
        self._search(Model, [('number', '<=', 1)])

    def test_inequalities_float(self):
        Model = self.env['test_new_api.mixed']
        Model.create([{}])
        Model.create([{'number2': n} for n in (-5, -3.3, 0.0, 0.1, 3, 4.5)])
        self._search(Model, [('number2', '>', 2)])
        self._search(Model, [('number2', '>', -2)])
        self._search(Model, [('number2', '>', 3)])
        self._search(Model, [('number2', '<', 1)])
        self._search(Model, [('number2', '<=', 1)])
