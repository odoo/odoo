# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import NewId
from odoo.fields import Command
from odoo.tests import TransactionCase


class TestSort(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.countries = cls.env['test_orm.country'].create([
            {'name': 'B'},
            {'name': 'A'},
            {'name': 'C'},
        ])
        b, a, c = cls.countries
        cls.cities = cls.env['test_orm.city'].create([
            {'name': 'c2', 'country_id': c.id},
            {'name': 'b1', 'country_id': b.id},
            {'name': 'b2', 'country_id': b.id},
            {'name': 'c1', 'country_id': c.id},
            {'name': 'a1', 'country_id': a.id},
            {'name': 'a2', 'country_id': a.id},
        ])

    def test_basic(self):
        db_result = self.env['test_orm.country'].search([])
        with self.assertQueryCount(1):
            # 1 query to fetch the fields, in practice it is already prefetched
            self.assertEqual(db_result.ids, self.countries.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.countries.sorted(reverse=True).ids)
        self.assertEqual(
            self.countries.sorted().mapped('name'),
            ['A', 'B', 'C']
        )

    def test_stable(self):
        self.assertEqual(
            self.cities.sorted('name', reverse=True).sorted('country_id.id'),
            self.cities.sorted(lambda c: (-c.country_id.id, c.name), reverse=True),
        )

    def test_basic_m2o(self):
        db_result = self.env['test_orm.city'].search([])
        with self.assertQueryCount(2):
            # 1 query to fetch the fields of both models,
            # in practice at least one is already prefetched or needs to be and the other is likely to be needed too
            self.assertEqual(db_result.ids, self.cities.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.cities.sorted(reverse=True).ids)
        self.assertEqual(
            self.cities.sorted().mapped('name'),
            ['a1', 'a2', 'b1', 'b2', 'c1', 'c2']
        )

    def test_basic_boolean(self):
        records = self.env['test_orm.model_active_field'].create([{'name': v} for v in 'abc'])
        records[1].active = False
        t_records = records.filtered('active')
        f_records = records - t_records
        with self.assertQueryCount(0):
            records.sorted('active, name')
        self.assertEqual(f_records + t_records, records.sorted('active, name'))
        self.assertEqual(t_records + f_records, records.sorted('active DESC, name'))

    def test_custom_m2o(self):
        order = 'country_id DESC, id ASC'
        db_result = self.env['test_orm.city'].search([], order=order)
        with self.assertQueryCount(2):
            # 1 query to fetch the fields of both models,
            # in practice at least one is already prefetched or needs to be and the other is likely to be needed too
            self.assertEqual(db_result.ids, self.cities.sorted(order).ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.cities.sorted(order, reverse=True).ids)
        self.assertEqual(
            self.cities.sorted(order).mapped('name'),
            ['c2', 'c1', 'b1', 'b2', 'a1', 'a2'],
        )

    def test_nulls(self):
        cities = self.env['test_orm.city'].create([
            {'name': 'not null 2', 'country_id': self.countries[2].id},
            {'name': 'not null 0', 'country_id': self.countries[0].id},
            {'name': False, 'country_id': self.countries[1].id},
            {'name': "", 'country_id': False},
            {'name': False, 'country_id': False},
            {'name': 'not null 1', 'country_id': self.countries[1].id},
        ])

        for order in [
            'country_id ASC, id',
            'country_id DESC, id',
            'country_id ASC NULLS FIRST, id',
            'country_id DESC NULLS FIRST, id',
            'country_id ASC NULLS LAST, id',
            'country_id DESC NULLS LAST, id',
            'name ASC, id',
            'name DESC, id',
            'name ASC NULLS FIRST, id',
            'name DESC NULLS FIRST, id',
            'name ASC NULLS LAST, id',
            'name DESC NULLS LAST, id',
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    self.env['test_orm.city'].search([('id', 'in', cities.ids)], order=order).mapped('name'),
                    cities.sorted(order).mapped('name')
                )

    def test_collation(self):
        countries = self.env['test_orm.country'].create([
            {'name': 'é'},
            {'name': 'e'},
            {'name': 'É'},
            {'name': '1.0'},
            {'name': '1,0'},
            {'name': '01'},
            {'name': '10'},
            {'name': '9'},
            {'name': 'Ab'},
            {'name': '👍'},
            {'name': 'AB'},
            {'name': 'Aa'},
            {'name': 'AA'},
        ])

        for order in [
            "name DESC",
            "name ASC",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    countries.search([('id', 'in', countries.ids)], order=order).mapped('name'),
                    countries.sorted(order).mapped('name')
                )

    def test_sorted_recursion(self):
        categories = self.env['test_orm.category'].search([])
        for order in [
            'parent ASC, id ASC',
            'parent ASC, id DESC',
            'parent DESC, id ASC',
            'parent DESC, id DESC',
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    categories.search([('id', 'in', categories.ids)], order=order).mapped('name'),
                    categories.sorted(order).mapped('name')
                )

    def test_compare_new_id(self):
        self.assertLess(5, NewId())
        self.assertLess(3, NewId(4))
        self.assertGreater(5, NewId(4))
        self.assertGreaterEqual(5, NewId(4))
        self.assertLess(4, NewId(4))
        self.assertGreater(NewId(5), NewId(4))

    def test_sorted_new_id(self):
        new_countries = self.env['test_orm.country'].concat(*[
            self.env['test_orm.country'].new(vals)
            for vals in [
                {'name': 'B'},
                {'name': 'A'},
                {'name': 'C'},
            ]
        ])

        order = 'id'  # new id after existing ones
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            self.countries.sorted(order) + new_countries.sorted(order),
        )

        order = 'id DESC'  # new id before existing ones
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            new_countries.sorted(order) + self.countries.sorted(order),
        )

    def test_prefetch(self):
        # sorted keeps the _prefetch_ids
        partners_with_children = self.env['res.partner'].create([
            {
                'name': 'required',
                'child_ids': [
                    Command.create({'name': 'z'}),
                    Command.create({'name': 'a'}),
                ],
            },
            {
                'name': 'required',
                'child_ids': [
                    Command.create({'name': 'z'}),
                    Command.create({'name': 'a'}),
                ],
            },
        ])
        partners_with_children.invalidate_model(['name'])
        # Only one query to fetch name of children of each partner
        with self.assertQueryCount(1):
            for partner in partners_with_children:
                partner.child_ids.sorted('id').mapped('name')
