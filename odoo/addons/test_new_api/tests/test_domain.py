# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged('domains')
class TestDomainNewApi(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.Cat = self.env['test_new_api.category']
        self.spam = self.Cat.create({
            'name': 'spam',
            'color': 1,
        })
        self.ham = self.Cat.create({
            'name': 'ham',
            'color': 2,
        })
        self.eggs = self.Cat.create({
            'name': 'eggs',
            'color': 3,
        })
        self.all_ids = self.spam | self.ham | self.eggs

    def _assertEqualDomain(self, domain_obj, domain_str):
        self.assertEquals(domain_obj.serialize(), domain_str)

    def test_sql_ops(self):
        self._assertEqualDomain(self.Cat().name == 'spam', [('name', '=', 'spam')])
        self._assertEqualDomain(self.Cat().name != 'ham', [('name', '!=', 'ham')])
        self._assertEqualDomain(self.Cat().color >= 1, [('color', '>=', 1)])
        self._assertEqualDomain(self.Cat().color > 2, [('color', '>', 2)])
        self._assertEqualDomain(self.Cat().color <= 3, [('color', '<=', 3)])
        self._assertEqualDomain(self.Cat().color < 2, [('color', '<', 2)])
        self._assertEqualDomain(self.Cat().color.has([1, 2]), [('color', 'in', [1, 2])])
        self._assertEqualDomain(self.Cat().color.hasnt([1, 2]), [('color', 'not in', [1, 2])])
        self._assertEqualDomain(self.Cat().name.maybe('foo'), [('name', '=?', 'foo')])
        self._assertEqualDomain(self.Cat().name.slike('eggs'), [('name', '=like', 'eggs')])
        self._assertEqualDomain(self.Cat().name.like('egg'), [('name', 'like', 'egg')])
        self._assertEqualDomain(self.Cat().name.not_like('ham'), [('name', 'not like', 'ham')])
        self._assertEqualDomain(self.Cat().name.silike('SPAM'), [('name', '=ilike', 'SPAM')])
        self._assertEqualDomain(self.Cat().name.ilike('EGG'), [('name', 'ilike', 'EGG')])
        self._assertEqualDomain(self.Cat().name.not_ilike('HAM'), [('name', 'not ilike', 'HAM')])
        self._assertEqualDomain(self.Cat().parent.child_of(1), [('parent', 'child_of', 1)])

    def test_domain_op_and(self):
        self._assertEqualDomain(
            (self.Cat().name == 'eggs') & (self.Cat().color > 2),
            ['&', ('name', '=', 'eggs'), ('color', '>', 2)],
        )

    def test_domain_op_or(self):
        self._assertEqualDomain(
            (self.Cat().name == 'ham') | (self.Cat().name == 'spam'),
            ['|', ('name', '=', 'ham'), ('name', '=', 'spam')],
        )

    def test_domain_op_not(self):
        self._assertEqualDomain(
            ~(self.Cat().color < 2), ['!', ('color', '<', 2)],
        )

    def test_domain_obj_search(self):
        self.assertEquals(self.Cat.search(self.Cat().name == 'spam'),
                self.spam)

    def test_domain_obj_search_count(self):
        self.assertEquals(self.Cat.search_count(self.Cat().name == 'eggs'), 1)

    def test_domain_obj_read_group(self):
        self.assertEquals(self.Cat.read_group(
            self.Cat().id.has(self.all_ids.ids), ['color'], ['name']),
            self.Cat.read_group(
                [('id', 'in', self.all_ids.ids)], ['color'], ['name'],
            )
        )

    def test_domain_obj_search_read(self):
        rec = self.Cat.search_read(self.Cat().name == 'eggs', ['name'])
        self.assertEquals(len(rec), 1)
        self.assertEquals(rec[0]['name'], 'eggs')

    def test_domain_obj_name_search(self):
        rec = self.Cat.name_search('eggs', self.Cat().id.has(self.all_ids.ids))
        self.assertEquals(len(rec), 1)
        self.assertEquals(rec[0][0], self.eggs.id)


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
