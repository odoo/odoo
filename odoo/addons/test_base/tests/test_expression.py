# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.models import BaseModel
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.osv import expression


class TestExpression(TransactionCase):

    def test_00_in_not_in_m2m(self):
        # Create 4 records with no m2m record, or one or two records (out of two record).
        RelationalModel = self.env['test_m2m_relational.model']
        rec_a = RelationalModel.create({'name': 'test_expression_record_A'})
        rec_b = RelationalModel.create({'name': 'test_expression_record_B'})

        records = self.env['test_base.model']
        a = records.create({'name': 'test_expression_record_A', 'many2many_ids': [(6, 0, [rec_a.id])]})
        b = records.create({'name': 'test_expression_record_B', 'many2many_ids': [(6, 0, [rec_b.id])]})
        ab = records.create({'name': 'test_expression_record_AB', 'many2many_ids': [(6, 0, [rec_a.id, rec_b.id])]})
        c = records.create({'name': 'test_expression_record_C'})

        # The tests.

        # On a one2many or many2many field, `in` should be read `contains` (and
        # `not in` should be read `doesn't contain`.

        with_a = records.search([('many2many_ids', 'in', [rec_a.id])])
        self.assertEqual(a + ab, with_a, "Search for many2many_ids in rec_a failed.")

        with_b = records.search([('many2many_ids', 'in', [rec_b.id])])
        self.assertEqual(b + ab, with_b, "Search for many2many_ids in rec_b failed.")

        # records with the record A or the record B.
        with_a_or_b = records.search([('many2many_ids', 'in', [rec_a.id, rec_b.id])])
        self.assertEqual(a + b + ab, with_a_or_b, "Search for many2many_ids contains rec_a or rec_b failed.")

        # Show that `contains list` is really `contains element or contains element`.
        with_a_or_with_b = records.search(['|', ('many2many_ids', 'in', [rec_a.id]), ('many2many_ids', 'in', [rec_b.id])])
        self.assertEqual(a + b + ab, with_a_or_with_b, "Search for many2many_ids contains rec_a or contains rec_b failed.")

        # If we change the OR in AND...
        with_a_and_b = records.search([('many2many_ids', 'in', [rec_a.id]), ('many2many_ids', 'in', [rec_b.id])])
        self.assertEqual(ab, with_a_and_b, "Search for many2many_ids contains rec_a and rec_b failed.")

        # records without record A and without record B.
        without_a_or_b = records.search([('many2many_ids', 'not in', [rec_a.id, rec_b.id])])
        self.assertFalse(without_a_or_b & (a + b + ab), "Search for many2many_ids doesn't contain rec_a or rec_b failed (1).")
        self.assertTrue(c in without_a_or_b, "Search for many2many_ids doesn't contain rec_a or rec_b failed (2).")

        # Show that `doesn't contain list` is really `doesn't contain element and doesn't contain element`.
        without_a_and_without_b = records.search([('many2many_ids', 'not in', [rec_a.id]), ('many2many_ids', 'not in', [rec_b.id])])
        self.assertFalse(without_a_and_without_b & (a + b + ab), "Search for many2many_ids doesn't contain rec_a and rec_b failed (1).")
        self.assertTrue(c in without_a_and_without_b, "Search for many2many_ids doesn't contain rec_a and rec_b failed (2).")

        # We can exclude any record containing the record A.
        without_a = records.search([('many2many_ids', 'not in', [rec_a.id])])
        self.assertTrue(a not in without_a, "Search for many2many_ids doesn't contain rec_a failed (1).")
        self.assertTrue(ab not in without_a, "Search for many2many_ids doesn't contain rec_a failed (2).")
        self.assertLessEqual(b + c, without_a, "Search for many2many_ids doesn't contain rec_a failed (3).")

        # (Obviously we can do the same for record B.)
        without_b = records.search([('many2many_ids', 'not in', [rec_b.id])])
        self.assertTrue(b not in without_b, "Search for many2many_ids doesn't contain rec_b failed (1).")
        self.assertTrue(ab not in without_b, "Search for many2many_ids doesn't contain rec_b failed (2).")
        self.assertLessEqual(a + c, without_b, "Search for many2many_ids doesn't contain rec_b failed (3).")

    def test_05_not_str_m2m(self):
        BaseTestModel = self.env['test_base.model']
        RelationalModel = self.env['test_m2m_relational.model']

        cids = {}
        for name in 'A B AB'.split():
            cids[name] = RelationalModel.create({'name': name}).id

        records_config = {
            '0': [],
            'a': [cids['A']],
            'b': [cids['B']],
            'ab': [cids['AB']],
            'a b': [cids['A'], cids['B']],
            'b ab': [cids['B'], cids['AB']],
        }
        pids = {}
        for name, rec_ids in records_config.items():
            pids[name] = BaseTestModel.create({'name': name, 'many2many_ids': [(6, 0, rec_ids)]}).id

        base_domain = [('id', 'in', list(pids.values()))]

        def test(op, value, expected):
            found_ids = BaseTestModel.search(base_domain + [('many2many_ids', op, value)]).ids
            expected_ids = [pids[name] for name in expected]
            self.assertItemsEqual(found_ids, expected_ids, '%s %r should return %r' % (op, value, expected))

        test('=', 'A', ['a', 'a b'])
        test('!=', 'B', ['0', 'a', 'ab'])
        test('like', 'A', ['a', 'ab', 'a b', 'b ab'])
        test('not ilike', 'B', ['0', 'a'])
        test('not like', 'AB', ['0', 'a', 'b', 'a b'])

    def test_10_hierarchy_in_m2m(self):
        BaseTestModel = self.env['test_base.model']
        RelationalModel = self.env['test_m2m_relational.model']

        # search through m2m relation
        records = BaseTestModel.search([('many2many_ids', 'child_of', self.ref('test_base.test_m2m_record_1'))])
        self.assertTrue(records)

        # setup test record categories
        record_root = RelationalModel.create({'name': 'Root category'})
        rec_0 = RelationalModel.create({'name': 'Parent category', 'parent_id': record_root.id})
        rec_1 = RelationalModel.create({'name': 'Child1', 'parent_id': rec_0.id})

        # test hierarchical search in m2m with child id (list of ids)
        rec = RelationalModel.search([('id', 'child_of', record_root.ids)])
        self.assertEqual(len(rec), 3)

        # test hierarchical search in m2m with child id (single id)
        rec = RelationalModel.search([('id', 'child_of', record_root.id)])
        self.assertEqual(len(rec), 3)

        # test hierarchical search in m2m with child ids
        rec = RelationalModel.search([('id', 'child_of', (rec_0 + rec_1).ids)])
        self.assertEqual(len(rec), 2)

        # test hierarchical search in m2m with child ids
        rec = RelationalModel.search([('id', 'child_of', rec_0.ids)])
        self.assertEqual(len(rec), 2)

        # test hierarchical search in m2m with child ids
        rec = RelationalModel.search([('id', 'child_of', rec_1.ids)])
        self.assertEqual(len(rec), 1)

        # test hierarchical search in m2m with an empty list
        rec = RelationalModel.search([('id', 'child_of', [])])
        self.assertEqual(len(rec), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            rec = RelationalModel.search([('id', 'child_of', False)])
        self.assertEqual(len(rec), 0)

        # test hierarchical search in m2m with parent id (list of ids)
        rec = RelationalModel.search([('id', 'parent_of', rec_1.ids)])
        self.assertEqual(len(rec), 3)

        # test hierarchical search in m2m with parent id (single id)
        rec = RelationalModel.search([('id', 'parent_of', rec_1.id)])
        self.assertEqual(len(rec), 3)

        # test hierarchical search in m2m with parent ids
        rec = RelationalModel.search([('id', 'parent_of', (record_root + rec_0).ids)])
        self.assertEqual(len(rec), 2)

        # test hierarchical search in m2m with parent ids
        rec = RelationalModel.search([('id', 'parent_of', rec_0.ids)])
        self.assertEqual(len(rec), 2)

        # test hierarchical search in m2m with parent ids
        rec = RelationalModel.search([('id', 'parent_of', record_root.ids)])
        self.assertEqual(len(rec), 1)

        # test hierarchical search in m2m with an empty list
        rec = RelationalModel.search([('id', 'parent_of', [])])
        self.assertEqual(len(rec), 0)

        # test hierarchical search in m2m with 'False' value
        with self.assertLogs('odoo.osv.expression'):
            rec = RelationalModel.search([('id', 'parent_of', False)])
        self.assertEqual(len(rec), 0)

    def test_10_equivalent_id(self):
        # equivalent queries
        BaseTestModel = self.env['test_base.model']
        non_exist_id = max(BaseTestModel.search([]).ids) + 1003
        res_0 = BaseTestModel.search([])
        res_1 = BaseTestModel.search([('name', 'not like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_1)
        res_2 = BaseTestModel.search([('id', 'not in', [non_exist_id])])
        self.assertEqual(res_0, res_2)
        res_3 = BaseTestModel.search([('id', 'not in', [])])
        self.assertEqual(res_0, res_3)
        res_4 = BaseTestModel.search([('id', '!=', False)])
        self.assertEqual(res_0, res_4)

        # equivalent queries, integer and string
        all_records = BaseTestModel.search([])
        self.assertTrue(len(all_records) > 1)
        one = all_records[0]
        others = all_records[1:]

        res_1 = BaseTestModel.search([('id', '=', one.id)])
        self.assertEqual(one, res_1)
        # BaseTestModel.search([('id', '!=', others)]) # not permitted
        res_2 = BaseTestModel.search([('id', 'not in', others.ids)])
        self.assertEqual(one, res_2)
        res_3 = BaseTestModel.search(['!', ('id', '!=', one.id)])
        self.assertEqual(one, res_3)
        res_4 = BaseTestModel.search(['!', ('id', 'in', others.ids)])
        self.assertEqual(one, res_4)
        # res_5 = BaseTestModel.search([('id', 'in', one)]) # TODO make it permitted, just like for child_of
        # self.assertEqual(one, res_5)
        res_6 = BaseTestModel.search([('id', 'in', [one.id])])
        self.assertEqual(one, res_6)
        res_7 = BaseTestModel.search([('name', '=', one.name)])
        self.assertEqual(one, res_7)
        res_8 = BaseTestModel.search([('name', 'in', [one.name])])
        # res_9 = BaseTestModel.search([('name', 'in', one.name)]) # TODO

    def test_15_m2o(self):
        BaseTestModel = self.env['test_base.model']

        # testing equality with name
        records = BaseTestModel.search([('parent_id', '=', 'Record-1')])
        self.assertTrue(records)

        # testing the in operator with name
        records = BaseTestModel.search([('parent_id', 'in', 'Record-1')])
        self.assertTrue(records)

        # testing the in operator with a list of names
        records = BaseTestModel.search([('parent_id', 'in', ['Record-1', 'Record-2'])])
        self.assertTrue(records)

        # check if many2one works with empty search list
        records = BaseTestModel.search([('many2one_id', 'in', [])])
        self.assertFalse(records)

        # create new many with record and record with no mane2one set
        rec = self.env['test_m2o_relational.model'].create({'name': 'Acme 2'})
        for i in range(4):
            BaseTestModel.create({'name': 'P of Acme %s' % i, 'many2one_id': rec.id})
            BaseTestModel.create({'name': 'P of All %s' % i, 'many2one_id': False})

        # check if many2one works with negative empty list
        all_records = BaseTestModel.search([])
        records = BaseTestModel.search(['|', ('many2one_id', 'not in', []), ('many2one_id', '=', False)])
        self.assertEqual(all_records, records, "not in [] fails")

        # check that many2one will pick the correct records with a list
        records = BaseTestModel.search([('many2one_id', 'in', [False])])
        self.assertTrue(len(records) >= 4, "We should have at least 4 records with no company")

        # check that many2one will exclude the correct records with a list
        records = BaseTestModel.search([('many2one_id', 'not in', [1])])
        self.assertTrue(len(records) >= 4, "We should have at least 4 records not related to company #1")

        # check that many2one will exclude the correct records with a list and False
        records = BaseTestModel.search(['|', ('many2one_id', 'not in', [1]),
                                        ('many2one_id', '=', False)])
        self.assertTrue(len(records) >= 8, "We should have at least 8 records not related to company #1")
        # check that multi-level expressions also work
        records = BaseTestModel.search([('many2one_id.many2one_id', 'in', [])])
        self.assertFalse(records)
        # check multi-level expressions with magic columns

        # check that multi-level expressions with negative op work
        all_records = BaseTestModel.search([('many2one_id', '!=', False)])
        res_records = BaseTestModel.search([('many2one_id.many2one_id', 'not in', [])])
        self.assertEqual(all_records, res_records, "not in [] fails")


        # Test the '(not) like/in' behavior. test record and its parent_id
        # column are used because parent_id is a many2one, allowing to test the
        # Null value, and there are actually some null and non-null values in
        # the demo data.
        all_records = BaseTestModel.search([])
        non_record_id = max(all_records.ids) + 1

        with_parent = all_records.filtered(lambda p: p.parent_id)
        without_parent = all_records.filtered(lambda p: not p.parent_id)
        with_many2one = all_records.filtered(lambda p: p.many2one_id)
        

        # We treat null values differently than in SQL. For instance in SQL:
        #   SELECT id FROM res_partner WHERE parent_id NOT IN (0)
        # will return only the records with non-null parent_id.
        #   SELECT id FROM res_partner WHERE parent_id IN (0)
        # will return expectedly nothing (our ids always begin at 1).
        # This means the union of those two results will give only some
        # records, but not all present in database.
        #
        # When using domains and the ORM's search method, we think it is
        # more intuitive that the union returns all the records, and that
        # a domain like ('parent_id', 'not in', [0]) will return all
        # the records. For instance, if you perform a search for the companies
        # that don't have OpenERP has a parent company, you expect to find,
        # among others, the companies that don't have parent company.
        #

        # existing values be treated similarly if we simply check that some
        # existing value belongs to them.
        res_0 = BaseTestModel.search([('parent_id', 'not like', 'probably_unexisting_name')]) # get all rows, included null parent_id
        self.assertEqual(res_0, all_records)
        res_1 = BaseTestModel.search([('parent_id', 'not in', [non_record_id])]) # get all rows, included null parent_id
        self.assertEqual(res_1, all_records)
        res_2 = BaseTestModel.search([('parent_id', '!=', False)]) # get rows with not null parent_id, deprecated syntax
        self.assertEqual(res_2, with_parent)
        res_3 = BaseTestModel.search([('parent_id', 'not in', [])]) # get all rows, included null parent_id
        self.assertEqual(res_3, all_records)
        res_4 = BaseTestModel.search([('parent_id', 'not in', [False])]) # get rows with not null parent_id
        self.assertEqual(res_4, with_parent)
        res_4b = BaseTestModel.search([('parent_id', 'not ilike', '')]) # get only rows without parent
        self.assertEqual(res_4b, without_parent)

        # The results of these queries, when combined with queries 0..4 must
        # give the whole set of ids.
        res_5 = BaseTestModel.search([('parent_id', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_5)
        res_6 = BaseTestModel.search([('parent_id', 'in', [non_record_id])])
        self.assertFalse(res_6)
        res_7 = BaseTestModel.search([('parent_id', '=', False)])
        self.assertEqual(res_7, without_parent)
        res_8 = BaseTestModel.search([('parent_id', 'in', [])])
        self.assertFalse(res_8)
        res_9 = BaseTestModel.search([('parent_id', 'in', [False])])
        self.assertEqual(res_9, without_parent)
        res_9b = BaseTestModel.search([('parent_id', 'ilike', '')]) # get those with a parent
        self.assertEqual(res_9b, with_parent)

        # These queries must return exactly the results than the queries 0..4,
        # i.e. not ... in ... must be the same as ... not in ... .
        res_10 = BaseTestModel.search(['!', ('parent_id', 'like', 'probably_unexisting_name')])
        self.assertEqual(res_0, res_10)
        res_11 = BaseTestModel.search(['!', ('parent_id', 'in', [non_record_id])])
        self.assertEqual(res_1, res_11)
        res_12 = BaseTestModel.search(['!', ('parent_id', '=', False)])
        self.assertEqual(res_2, res_12)
        res_13 = BaseTestModel.search(['!', ('parent_id', 'in', [])])
        self.assertEqual(res_3, res_13)
        res_14 = BaseTestModel.search(['!', ('parent_id', 'in', [False])])
        self.assertEqual(res_4, res_14)

        # Testing many2one field is not enough, a regular char field is tested
        res_15 = BaseTestModel.search([('many2one_id', 'in', [])])
        self.assertFalse(res_15)
        res_16 = BaseTestModel.search([('many2one_id', 'not in', [])])
        self.assertEqual(res_16, all_records)
        res_17 = BaseTestModel.search([('many2one_id', '!=', False)])
        self.assertEqual(res_17, with_many2one)
        # check behavior for required many2one fields: m2o_required_id is required
        ReqiredModel = self.env['test_required.model']
        required_recs = ReqiredModel.search([])
        res_101 = ReqiredModel.search([('m2o_required_id', 'not ilike', '')])  # get no records
        self.assertFalse(res_101)
        res_102 = ReqiredModel.search([('m2o_required_id', 'ilike', '')])  # get all records
        self.assertEqual(res_102, required_recs)

    def test_in_operator(self):
        """ check that we can use the 'in' operator for plain fields """
        records = self.env['test_base.model'].search([('sequence', 'in', [1, 2, 10, 20])])
        self.assertTrue(records)

    def test_15_o2m(self):
        BaseTestModel = self.env['test_base.model']

        # test one2many operator with empty search list
        records = BaseTestModel.search([('child_ids', 'in', [])])
        self.assertFalse(records)

        # test one2many operator with False
        records = BaseTestModel.search([('child_ids', '=', False)])
        for record in records:
            self.assertFalse(record.child_ids)

        # verify domain evaluation for one2many != False and one2many == False
        records = BaseTestModel.search([])
        parents = records.search([('child_ids', '!=', False)])
        self.assertEqual(parents, records.filtered(lambda c: c.child_ids))
        leafs = records.search([('child_ids', '=', False)])
        self.assertEqual(leafs, records.filtered(lambda c: not c.child_ids))

        # test many2many operator with empty search list
        records = BaseTestModel.search([('many2many_ids', 'in', [])])
        self.assertFalse(records)

        # test many2many operator with False
        records = BaseTestModel.search([('many2many_ids', '=', False)])
        for record in records:
            self.assertFalse(record.many2many_ids)

        # filtering on nonexistent value across x2many should return nothing
        records = BaseTestModel.search([('child_ids.name', '=', 'foo')])
        self.assertFalse(records)

    def test_15_equivalent_one2many_1(self):
        BaseTestModel = self.env['test_base.model']
        rec_1 = BaseTestModel.create({'name': 'Acme 3'})
        rec_2 = BaseTestModel.create({'name': 'Acme 4', 'parent_id': rec_1.id})

        # one2many towards same model
        res_1 = BaseTestModel.search([('child_ids', 'in', rec_1.child_ids.ids)])  # any company having a child of company3 as child
        self.assertEqual(res_1, rec_1)
        res_2 = BaseTestModel.search([('child_ids', 'in', rec_1.child_ids[0].ids)])  # any company having the first child of company3 as child
        self.assertEqual(res_2, rec_1)

        # child_of x returns x and its children (direct or not).
        expected = rec_1 + rec_2
        res_1 = BaseTestModel.search([('id', 'child_of', [rec_1.id])])
        self.assertEqual(res_1, expected)
        res_2 = BaseTestModel.search([('id', 'child_of', rec_1.id)])
        self.assertEqual(res_2, expected)
        res_3 = BaseTestModel.search([('id', 'child_of', [rec_1.name])])
        self.assertEqual(res_3, expected)
        res_4 = BaseTestModel.search([('id', 'child_of', rec_1.name)])
        self.assertEqual(res_4, expected)

        # parent_of x returns x and its parents (direct or not).
        expected = rec_1 + rec_2
        res_1 = BaseTestModel.search([('id', 'parent_of', [rec_2.id])])
        self.assertEqual(res_1, expected)
        res_2 = BaseTestModel.search([('id', 'parent_of', rec_2.id)])
        self.assertEqual(res_2, expected)
        res_3 = BaseTestModel.search([('id', 'parent_of', [rec_2.name])])
        self.assertEqual(res_3, expected)
        res_4 = BaseTestModel.search([('id', 'parent_of', rec_2.name)])
        self.assertEqual(res_4, expected)

        # try testing real subsets with IN/NOT IN
        BaseTestModel = self.env['test_base.model']
        O2mRelationModel = self.env['test_o2m_relational.model']
        p1, _ = BaseTestModel.name_create("Dédé Boitaclou")
        p2, _ = BaseTestModel.name_create("Raoulette Pizza O'poil")
        u1a = O2mRelationModel.create({'name': 'dbo', 'model_id': p1}).id
        u1b = O2mRelationModel.create({'name': 'rco', 'model_id': p1}).id
        u2 = O2mRelationModel.create({'name': 'xmo', 'model_id': p2}).id
        self.assertEqual([p1], BaseTestModel.search([('one2many_ids', 'in', u1a)]).ids, "o2m IN accept single int on right side")
        self.assertEqual([p1], BaseTestModel.search([('one2many_ids', '=', 'dbo')]).ids, "o2m NOT IN matches none on the right side")
        self.assertEqual([], BaseTestModel.search([('one2many_ids', 'in', [10000])]).ids, "o2m NOT IN matches none on the right side")
        self.assertEqual([p1, p2], BaseTestModel.search([('one2many_ids', 'in', [u1a, u2])]).ids, "o2m IN matches any on the right side")
        all_ids = BaseTestModel.search([]).ids
        self.assertEqual(set(all_ids) - set([p1]), set(BaseTestModel.search([('one2many_ids', 'not in', u1a)]).ids), "o2m NOT IN matches none on the right side")
        self.assertEqual(set(all_ids) - set([p1]), set(BaseTestModel.search([('one2many_ids', '!=', 'dbo')]).ids), "o2m NOT IN matches none on the right side")
        self.assertEqual(set(all_ids) - set([p1, p2]), set(BaseTestModel.search([('one2many_ids', 'not in', [u1b, u2])]).ids), "o2m NOT IN matches none on the right side")

    def test_15_equivalent_one2many_2(self):
        BaseTestModel = self.env['test_base.model']
        O2mRelationModel = self.env['test_o2m_relational.model']

        record = BaseTestModel.create({'name': 'Test'})
        relational_record = O2mRelationModel.create({'name': 'relational record', 'model_id': record.id})
        non_exist_record = relational_record.id + 1000

        # search the records via its rates one2many (the one2many must point back at the record)
        rec_1 = O2mRelationModel.search([('name', 'not like', 'probably_unexisting_name')])
        rec_2 = O2mRelationModel.search([('id', 'not in', [non_exist_record])])
        self.assertEqual(rec_1, rec_2)
        rec_3 = O2mRelationModel.search([('id', 'not in', [])])
        self.assertEqual(rec_1, rec_3)

        # one2many towards another model
        res_3 = BaseTestModel.search([('one2many_ids', 'in', record.one2many_ids.ids)])
        self.assertEqual(res_3, record)
        res_4 = BaseTestModel.search([('one2many_ids', 'in', record.one2many_ids[0].ids)])
        self.assertEqual(res_4, record)
        res_5 = BaseTestModel.search([('one2many_ids', 'in', record.one2many_ids[0].id)])
        self.assertEqual(res_5, record)
        res_9 = BaseTestModel.search([('one2many_ids', 'like', 'probably_unexisting_name')])
        self.assertFalse(res_9)
        # get the records referenced by some one2many records using a weird negative domain
        res_10 = BaseTestModel.search([('one2many_ids', 'not like', 'probably_unexisting_name')])
        res_11 = BaseTestModel.search([('one2many_ids', 'not in', [non_exist_record])])
        self.assertEqual(res_10, res_11)
        res_13 = BaseTestModel.search([('one2many_ids', 'not in', [])])
        self.assertEqual(res_10, res_13)

    def test_20_expression_parse(self):
        # TDE note: those tests have been added when refactoring the expression.parse() method.
        # They come in addition to the already existing tests; maybe some tests
        # will be a bit redundant
        BaseTestModel = self.env['test_base.model']

        # Create users
        a = BaseTestModel.create({'name': 'test_A'})
        b1 = BaseTestModel.create({'name': 'test_B'})
        b2 = BaseTestModel.create({'name': 'test_B2', 'parent_id': b1.id})

        # Test1: simple inheritance
        records = BaseTestModel.search([('name', 'like', 'test')])
        self.assertEqual(records, a + b1 + b2, 'searching through inheritance failed')
        records = BaseTestModel.search([('name', '=', 'test_B')])
        self.assertEqual(records, b1, 'searching through inheritance failed')

        # Test2: inheritance + relational fields
        records = BaseTestModel.search([('child_ids.name', 'like', 'test_B')])
        self.assertEqual(records, b1, 'searching through inheritance failed')

        # Special =? operator mean "is equal if right is set, otherwise always True"
        records = BaseTestModel.search([('name', 'like', 'test'), ('parent_id', '=?', False)])
        self.assertEqual(records, a + b1 + b2, '(x =? False) failed')
        records = BaseTestModel.search([('name', 'like', 'test'), ('parent_id', '=?', b1.id)])
        self.assertEqual(records, b2, '(x =? id) failed')

    def test_30_normalize_domain(self):
        norm_domain = domain = ['&', (1, '=', 1), ('a', '=', 'b')]
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Normalized domains should be left untouched")
        domain = [('x', 'in', ['y', 'z']), ('a.v', '=', 'e'), '|', '|', ('a', '=', 'b'), '!', ('c', '>', 'd'), ('e', '!=', 'f'), ('g', '=', 'h')]
        norm_domain = ['&', '&', '&'] + domain
        self.assertEqual(norm_domain, expression.normalize_domain(domain), "Non-normalized domains should be properly normalized")

    def test_40_negating_long_expression(self):
        source = ['!', '&', ('user_id', '=', 4), ('partner_id', 'in', [1, 2])]
        expect = ['|', ('user_id', '!=', 4), ('partner_id', 'not in', [1, 2])]
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on expression applied wrongly")

        pos_leaves = [[('a', 'in', [])], [('d', '!=', 3)]]
        neg_leaves = [[('a', 'not in', [])], [('d', '=', 3)]]

        source = expression.OR([expression.AND(pos_leaves)] * 1000)
        expect = source
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on long expression without negation operator should not alter it")

        source = ['!'] + source
        expect = expression.AND([expression.OR(neg_leaves)] * 1000)
        self.assertEqual(expression.distribute_not(source), expect,
            "distribute_not on long expression applied wrongly")

    def test_accent(self):
        if not self.registry.has_unaccent:
            return
        BaseTestModel = self.env['test_base.model']
        helene = BaseTestModel.create({'name': u'Hélène'})
        self.assertEqual(helene, BaseTestModel.search([('name', 'ilike', 'Helene')]))
        self.assertEqual(helene, BaseTestModel.search([('name', 'ilike', 'hélène')]))
        self.assertNotIn(helene, BaseTestModel.search([('name', 'not ilike', 'Helene')]))
        self.assertNotIn(helene, BaseTestModel.search([('name', 'not ilike', 'hélène')]))

    def test_like_wildcards(self):
        # check that =like/=ilike expressions are working on an untranslated field
        BaseTestModel = self.env['test_base.model']
        records = BaseTestModel.search([('name', '=like', 'R__or_-1')])
        self.assertTrue(len(records) == 1, "Must match one record (Record-1)")
        records = BaseTestModel.search([('name', '=ilike', 'R%')])
        self.assertTrue(len(records) >= 6, "Must match all records start with R")

        # TODO: RGA: is it require to create translation entries(demo data) ?
        # check that =like/=ilike expressions are working on translated field
        TranslationModel = self.env['test_translation.model']
        records = TranslationModel.search([('name', '=like', 'R__or_-1')])
        self.assertTrue(len(records) == 1, "Must match Record-1 only")
        records = TranslationModel.search([('name', '=ilike', 'R%')])
        self.assertTrue(len(records) == 2, "Must match only Records with names starting with R")

    def test_translate_search(self):
        BaseTestModel = self.env['test_base.model']
        record = self.env.ref('test_base.test_model_data_1')
        domains = [
            [('name', '=', 'Record-1')],
            [('name', 'in', ['Record-1', 'Care Bears'])],
        ]

        for domain in domains:
            result = BaseTestModel.search(domain)
            self.assertEqual(result, record)

    def test_long_table_alias(self):
        # To test the 64 characters limit for table aliases in PostgreSQL
        # TODO: RGA: I don't understand why ?
        self.patch_order('test_base.model', 'parent_id')
        self.patch_order('test_m2m_relational.model', 'parent_id,name')
        self.patch_order('test_m2o_relational.model', 'many2one_id')
        self.env['test_base.model'].search([('name', '=', 'test')])

    @mute_logger('odoo.sql_db')
    def test_invalid(self):
        """ verify that invalid expressions are refused, even for magic fields """
        BaseTestModel = self.env['test_base.model']

        with self.assertRaises(ValueError):
            BaseTestModel.search([('does_not_exist', '=', 'foo')])

        with self.assertRaises(ValueError):
            BaseTestModel.search([('create_date', '>>', 'foo')])

        with self.assertRaises(psycopg2.DataError):
            BaseTestModel.search([('create_date', '=', "1970-01-01'); --")])

    def test_active(self):
        # testing for many2many field with category office and active=False
        BaseTestModel = self.env['test_base.model']
        vals = {
            'name': 'Odoo Test',
            'active': False,
            'many2many_ids': [(6, 0, [self.ref("test_base.test_m2m_record_1")])],
            'child_ids': [(0, 0, {'name': 'address of Odoo Test', 'many2one_id': self.ref("test_base.test_model_data_1")})],
        }
        BaseTestModel.create(vals)
        record = BaseTestModel.search([('many2many_ids', 'ilike', 'record'), ('active', '=', False)])
        self.assertTrue(record, "Record Found with name 'record' and active False.")

        # testing for one2many field with record and active=False
        record = BaseTestModel.search([('child_ids.many2one_id', '=', 'Many2one Record-1'), ('active', '=', False)])
        self.assertTrue(record, "Record Found with record and active False.")

    def test_lp1071710(self):
        """ Check that we can exclude translated fields (bug lp:1071710) """
        translationModel = self.env['test_translation.model']
        record = translationModel.create({'name': 'Belgium'})
        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'test_translation.model,name',
            'module': 'test_base',
            'lang': 'fr_FR',
            'res_id': record.id,
            'value': 'Belgique',
            'state': 'translated',
        })
        self.env.ref('test_base.test_model_data_1').translate_id = record
        not_be = translationModel.with_context(lang='fr_FR').search([('name', '!=', 'Belgique')])
        self.assertNotIn(record, not_be)

        BaseTestModel = self.env['test_base.model']
        record = BaseTestModel.search([('name', '=', 'Record-1')])
        not_be = BaseTestModel.search([('translate_id', '!=', 'Belgium')])
        self.assertNotIn(record, not_be)
        not_be = BaseTestModel.with_context(lang='fr_FR').search([('translate_id', '!=', 'Belgique')])
        self.assertNotIn(record, not_be)

    def test_or_with_implicit_and(self):
        # Check that when using expression.OR on a list of domains with at least one
        # implicit '&' the returned domain is the expected result.
        # from #24038
        d1 = [('foo', '=', 1), ('bar', '=', 1)]
        d2 = ['&', ('foo', '=', 2), ('bar', '=', 2)]

        expected = ['|', '&', ('foo', '=', 1), ('bar', '=', 1),
                         '&', ('foo', '=', 2), ('bar', '=', 2)]
        self.assertEqual(expression.OR([d1, d2]), expected)


class TestAutoJoin(TransactionCase):

    def setUp(self):
        super(TestAutoJoin, self).setUp()
        # Mock BaseModel._where_calc(), to be able to proceed to some tests about generated expression
        self._reinit_mock()
        BaseTestModel_where_calc = BaseModel._where_calc

        def _where_calc(model, *args, **kwargs):
            """ Mock `_where_calc` to be able to test its results. Store them
                into some internal variable for latter processing. """
            query = BaseTestModel_where_calc(model, *args, **kwargs)
            self.query_list.append(query)
            return query

        self.patch(BaseModel, '_where_calc', _where_calc)

    def _reinit_mock(self):
        self.query_list = []

    def test_auto_join(self):
        unaccent = expression.get_unaccent_wrapper(self.cr)

        # Get models
        BaseTestModel = self.env['test_base.model']
        M2oRelationalModel = self.env['test_m2o_relational.model']
        O2mRelationalModel = self.env['test_o2m_relational.model']
        
        # Get test columns
        def patch_auto_join(model, fname, value):
            self.patch(model._fields[fname], 'auto_join', value)

        def patch_domain(model, fname, value):
            self.patch(model._fields[fname], 'domain', value)

        rec_1 = self.env.ref('test_base.test_o2m_record_1')
        rec_2 = self.env.ref('test_base.test_o2m_record_1')

        # Create demo data: records and bank object
        p_a = BaseTestModel.create({'name': 'test__A', 'many2one_id': rec_1.id})
        p_b = BaseTestModel.create({'name': 'test__B', 'many2one_id': rec_2.id})
        p_aa = BaseTestModel.create({'name': 'test__AA', 'parent_id': p_a.id, 'many2one_id': rec_1.id})
        p_ab = BaseTestModel.create({'name': 'test__AB', 'parent_id': p_a.id, 'many2one_id': rec_2.id})
        p_ba = BaseTestModel.create({'name': 'test__BA', 'parent_id': p_b.id, 'many2one_id': rec_1.id})
        b_aa = O2mRelationalModel.create({'name': '123', 'model_id': p_aa.id})
        b_ab = O2mRelationalModel.create({'name': '456', 'model_id': p_ab.id})
        b_ba = O2mRelationalModel.create({'name': '789', 'model_id': p_ba.id})

        # --------------------------------------------------
        # Test1: basics about the attribute
        # --------------------------------------------------

        patch_auto_join(BaseTestModel, 'many2many_ids', True)
        with self.assertRaises(NotImplementedError):
            BaseTestModel.search([('many2many_ids.name', '=', 'foo')])

        # --------------------------------------------------
        # Test2: one2many
        # --------------------------------------------------

        name_test = '12'

        # Do: one2many without _auto_join
        self._reinit_mock()
        records = BaseTestModel.search([('one2many_ids.name', 'like', name_test)])
        # Test result
        self.assertEqual(records, p_aa,
            "_auto_join off: ('one2many_ids.name', 'like', '..'): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join off: ('one2many_ids.name', 'like', '..') should produce 2 queries (1 in test_o2m_relational_model, 1 on test_base_model)")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('test_o2m_relational_model', sql_query[0],
            "_auto_join off: ('one2many_ids.name', 'like', '..') first query incorrect main table")

        expected = "%s like %s" % (unaccent('"test_o2m_relational_model"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join off: ('one2many_ids.name', 'like', '..') first query incorrect where condition")

        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join off: ('one2many_ids.name', 'like', '..') first query incorrect parameter")
        sql_query = self.query_list[1].get_sql()
        self.assertIn('test_base_model', sql_query[0],
            "_auto_join off: ('one2many_ids.name', 'like', '..') second query incorrect main table")
        self.assertIn('"test_base_model"."id" in (%s)', sql_query[1],
            "_auto_join off: ('one2many_ids.name', 'like', '..') second query incorrect where condition")
        self.assertIn(p_aa.id, sql_query[2],
            "_auto_join off: ('one2many_ids.name', 'like', '..') second query incorrect parameter")


        # Do: cascaded one2many without _auto_join
        self._reinit_mock()
        records = BaseTestModel.search([('child_ids.one2many_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result
        self.assertEqual(records, p_a + p_b,
            "_auto_join off: ('child_ids.one2many_ids.id', 'in', [..]): incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('child_ids.one2many_ids.id', 'in', [..]) should produce 3 queries (1 in related model, 2 on test_mode)")
        # Do: one2many with _auto_join
        patch_auto_join(records, 'one2many_ids', True)
        self._reinit_mock()
        records = BaseTestModel.search([('one2many_ids.name', 'like', name_test)])
        # Test result
        self.assertEqual(records, p_aa,
            "_auto_join on: ('one2many_ids.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('one2many_ids.name', 'like', '..') should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on: ('one2many_ids.name', 'like', '..') query incorrect main table")
        self.assertIn('"test_o2m_relational_model" as "test_base_model__one2many_ids"', sql_query[0],
            "_auto_join on: ('one2many_ids.name', 'like', '..') query incorrect join")
        expected = "%s like %s" % (unaccent('"test_base_model__one2many_ids"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('one2many_ids.name', 'like', '..') query incorrect where condition")
        self.assertIn('"test_base_model"."id"="test_base_model__one2many_ids"."model_id"', sql_query[1],
            "_auto_join on: ('one2many_ids.name', 'like', '..') query incorrect join condition")
        self.assertIn('%' + name_test + '%', sql_query[2],
            "_auto_join on: ('one2many_ids.name', 'like', '..') query incorrect parameter")

        # Do: one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        record_ids = [b_aa.id, b_ab.id]
        records = BaseTestModel.search([('one2many_ids.id', 'in', record_ids)])
        # Test result
        self.assertEqual(records, p_aa + p_ab,
            "_auto_join on: ('bank_ids.id', 'in', [..]) incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('one2many_ids.id', 'in', [..]) should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on: ('one2many_ids.id', 'in', [..]) query incorrect main table")
        self.assertIn('"test_base_model__one2many_ids"."id" in (%s,%s)', sql_query[1],
            "_auto_join on: ('one2many_ids.id', 'in', [..]) query incorrect where condition")
        self.assertLessEqual(set(record_ids), set(sql_query[2]),
            "_auto_join on: ('one2many_ids.id', 'in', [..]) query incorrect parameter")

        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        patch_auto_join(BaseTestModel, 'child_ids', True)
        self._reinit_mock()
        record_ids = [b_aa.id, b_ba.id]
        records = BaseTestModel.search([('child_ids.one2many_ids.id', 'in', record_ids)])
        # Test result
        self.assertEqual(records, p_a + p_b,
            "_auto_join on: ('child_ids.one2many_ids.id', 'not in', [..]): incorrect result")
        # # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) incorrect main table")
        self.assertIn('"test_base_model" as "test_base_model__child_ids"', sql_query[0],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect join")
        self.assertIn('"test_o2m_relational_model" as "test_base_model__child_ids__one2many_ids"', sql_query[0],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect join")
        self.assertIn('"test_base_model__child_ids__one2many_ids"."id" in (%s,%s)', sql_query[1],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect where condition")
        self.assertIn('"test_base_model"."id"="test_base_model__child_ids"."parent_id"', sql_query[1],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect join condition")
        self.assertIn('"test_base_model__child_ids"."id"="test_base_model__child_ids__one2many_ids"."model_id"', sql_query[1],
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect join condition")
        self.assertLessEqual(set(record_ids), set(sql_query[2][-2:]),
            "_auto_join on: ('child_ids.one2many_ids.id', 'in', [..]) query incorrect parameter")

        # --------------------------------------------------
        # Test3: many2one
        # --------------------------------------------------
        name_test = 'Rec'

        # Do: many2one without _auto_join
        self._reinit_mock()
        records = BaseTestModel.search([('many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, records,
            "_auto_join off: ('many2one_id.many2one_level_id.name'', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 3,
            "_auto_join off: ('many2one_id.many2one_level_id.name', 'like', '..') should produce 3 queries (1 on relational_many2one_level, 1 on relational_many2one, 1 on base_test_model)")

        # Do: many2one with 1 _auto_join on the first many2one
        patch_auto_join(BaseTestModel, 'many2one_id', True)
        self._reinit_mock()
        records = BaseTestModel.search([('many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, records,
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') should produce 2 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_m2o_level_1_model"', sql_query[0],
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 1 incorrect main table")

        expected = "%s like %s" % (unaccent('"test_m2o_level_1_model"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 1 incorrect where condition")

        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 1 incorrect parameter")
        sql_query = self.query_list[1].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 2 incorrect main table")
        self.assertIn('"test_m2o_relational_model" as "test_base_model__many2one_id"', sql_query[0],
            "_auto_join on for many2one_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 2 incorrect join")
        self.assertIn('"test_base_model__many2one_id"."many2one_level_id" in (%s,%s)', sql_query[1],
            "_auto_join on for state_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 2 incorrect where condition")
        self.assertIn('"test_base_model"."many2one_id"="test_base_model__many2one_id"."id"', sql_query[1],
            "_auto_join on for state_id: ('many2one_id.many2one_level_id.name', 'like', '..') query 2 incorrect join condition")

        # Do: many2one with 1 _auto_join on the second many2one
        patch_auto_join(BaseTestModel, 'many2one_id', False)
        patch_auto_join(M2oRelationalModel, 'many2one_level_id', True)
        self._reinit_mock()
        records = BaseTestModel.search([('many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, records,
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 2,
            "_auto_join on for country_id: ('many2one_id.many2one_level_id.name, 'like', '..') should produce 2 query")
        # -- first query
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_m2o_level_1_model"', sql_query[0],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 1 incorrect main table")
        self.assertIn('"test_m2o_level_1_model" as "test_m2o_relational_model__many2one_level_id"', sql_query[0],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 1 incorrect join")

        expected = "%s like %s" % (unaccent('"test_m2o_relational_model__many2one_level_id"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 1 incorrect where condition")
        
        self.assertIn('"test_m2o_relational_model"."many2one_level_id"="test_m2o_relational_model__many2one_level_id"."id"', sql_query[1],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 1 incorrect join condition")
        self.assertEqual(['%' + name_test + '%'], sql_query[2],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 1 incorrect parameter")
        # -- second query
        sql_query = self.query_list[1].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 2 incorrect main table")
        self.assertIn('"test_base_model"."many2one_id" in', sql_query[1],
            "_auto_join on for many2one_level_id: ('many2one_id.many2one_level_id.name, 'like', '..') query 2 incorrect where condition")

        # Do: many2one with 2 _auto_join
        patch_auto_join(BaseTestModel, 'many2one_id', True)
        patch_auto_join(M2oRelationalModel, 'many2one_level_id', True)
        self._reinit_mock()
        records = BaseTestModel.search([('many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b + p_aa + p_ab + p_ba, records,
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') should produce 1 query")
        sql_query = self.query_list[0].get_sql()
        self.assertIn('"test_base_model"', sql_query[0],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect main table")
        self.assertIn('"test_m2o_relational_model" as "test_base_model__many2one_id"', sql_query[0],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect join")
        self.assertIn('"test_m2o_level_1_model" as "test_base_model__many2one_id__many2one_level_id"', sql_query[0],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect join")

        expected = "%s like %s" % (unaccent('"test_base_model__many2one_id__many2one_level_id"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect where condition")
        
        self.assertIn('"test_base_model"."many2one_id"="test_base_model__many2one_id"."id"', sql_query[1],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect join condition")
        self.assertIn('"test_base_model__many2one_id"."many2one_level_id"="test_base_model__many2one_id__many2one_level_id"."id"', sql_query[1],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect join condition")
        self.assertIn('%' + name_test + '%', sql_query[2],
            "_auto_join on: ('many2one_id.many2one_level_id.name', 'like', '..') query incorrect parameter")

        # --------------------------------------------------
        # Test4: domain attribute on one2many fields
        # --------------------------------------------------

        patch_auto_join(BaseTestModel, 'child_ids', True)
        patch_auto_join(BaseTestModel, 'one2many_ids', True)
        patch_domain(BaseTestModel, 'child_ids', lambda self: ['!', ('name', '=', self._name)])
        patch_domain(BaseTestModel, 'one2many_ids', [('name', 'like', '2')])
        # Do: 2 cascaded one2many with _auto_join, test final leaf is an id
        self._reinit_mock()
        records = BaseTestModel.search(['&', (1, '=', 1), ('child_ids.one2many_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result: at least one of our added data
        self.assertLessEqual(p_a, records,
            "_auto_join on one2many with domains incorrect result")
        self.assertFalse((p_ab + p_ba) & records,
            "_auto_join on one2many with domains incorrect result")
        # Test produced queries that domains effectively present
        sql_query = self.query_list[0].get_sql()
        expected = "%s like %s" % (unaccent('"test_base_model__child_ids__one2many_ids"."name"::text'), unaccent('%s'))
        self.assertIn(expected, sql_query[1],
            "_auto_join on one2many with domains incorrect result")
        # TDE TODO: check first domain has a correct table name
        self.assertIn('"test_base_model__child_ids"."name" = %s', sql_query[1],
            "_auto_join on one2many with domains incorrect result")

        patch_domain(BaseTestModel, 'child_ids', lambda self: [('name', '=', '__%s' % self._name)])
        self._reinit_mock()
        records = BaseTestModel.search(['&', (1, '=', 1), ('child_ids.one2many_ids.id', 'in', [b_aa.id, b_ba.id])])
        # Test result: no one
        self.assertFalse(records,
            "_auto_join on one2many with domains incorrect result")

        # ----------------------------------------
        # Test5: result-based tests
        # ----------------------------------------
        patch_auto_join(BaseTestModel, 'one2many_ids', False)
        patch_auto_join(BaseTestModel, 'child_ids', False)
        patch_auto_join(BaseTestModel, 'many2one_id', False)
        patch_auto_join(BaseTestModel, 'parent_id', False)
        patch_auto_join(M2oRelationalModel, 'many2one_level_id', False)
        patch_domain(BaseTestModel, 'child_ids', [])
        patch_domain(BaseTestModel, 'one2many_ids', [])

        # Do: ('child_ids.many2one_id.many2one_level_id.name', 'like', '..') without _auto_join
        self._reinit_mock()
        records = BaseTestModel.search([('child_ids.many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b, records,
            "_auto_join off: ('hild_ids.many2one_id.many2one_level_id.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 4,
            "_auto_join off: ('child_ids.many2one_id.many2one_level_id.name', 'like', '..') number of queries incorrect")

        # Do: ('child_ids.state_id.country_id.code', 'like', '..') with _auto_join
        patch_auto_join(BaseTestModel, 'child_ids', True)
        patch_auto_join(BaseTestModel, 'many2one_id', True)
        patch_auto_join(M2oRelationalModel, 'many2one_level_id', True)
        self._reinit_mock()
        records = BaseTestModel.search([('child_ids.many2one_id.many2one_level_id.name', 'like', name_test)])
        # Test result: at least our added data + demo data
        self.assertLessEqual(p_a + p_b, records,
            "_auto_join on: ('child_ids.many2one_id.many2one_level_id.name', 'like', '..') incorrect result")
        # Test produced queries
        self.assertEqual(len(self.query_list), 1,
            "_auto_join on: ('child_ids.many2one_id.many2one_level_id.name', 'like', '..') number of queries incorrect")