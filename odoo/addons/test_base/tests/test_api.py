# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import mute_logger
from odoo.tests import common
from odoo.exceptions import AccessError


class TestAPI(common.TransactionCase):
    """ test the new API of the ORM """

    def assertIsRecordset(self, value, model):
        self.assertIsInstance(value, models.BaseModel)
        self.assertEqual(value._name, model)

    def assertIsRecord(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertTrue(len(value) <= 1)

    def assertIsNull(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertFalse(value)

    @mute_logger('odoo.models')
    def test_00_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'r')]
        records = self.env['test_base.model'].search(domain)

        # result is a collection of browse records
        self.assertTrue(records)

        # records and its contents are instance of the model
        self.assertIsRecordset(records, 'test_base.model')
        for p in records:
            self.assertIsRecord(p, 'test_base.model')

    @mute_logger('odoo.models')
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        records1 = self.env['test_base.model'].search([], offset=2)
        records2 = self.env['test_base.model'].search([])[2:]
        self.assertIsRecordset(records1, 'test_base.model')
        self.assertIsRecordset(records2, 'test_base.model')
        self.assertEqual(list(records1), list(records2))

    @mute_logger('odoo.models')
    def test_02_query_limit(self):
        """ Build a recordset with offset, and check equivalence. """
        records1 = self.env['test_base.model'].search([], limit=3)
        records2 = self.env['test_base.model'].search([])[:3]
        self.assertIsRecordset(records1, 'test_base.model')
        self.assertIsRecordset(records2, 'test_base.model')
        self.assertEqual(list(records1), list(records2))

    @mute_logger('odoo.models')
    def test_03_query_offset_limit(self):
        """ Build a recordset with offset and limit, and check equivalence. """
        records1 = self.env['test_base.model'].search([], offset=2, limit=2)
        records2 = self.env['test_base.model'].search([])[2:4]
        self.assertIsRecordset(records1, 'test_base.model')
        self.assertIsRecordset(records2, 'test_base.model')
        self.assertEqual(list(records1), list(records2))

    @mute_logger('odoo.models')
    def test_04_query_count(self):
        """ Test the search method with count=True. """
        self.cr.execute("SELECT COUNT(*) FROM test_base_model WHERE active")
        count1 = self.cr.fetchone()[0]
        count2 = self.env['test_base.model'].search([], count=True)
        self.assertIsInstance(count1, int)
        self.assertIsInstance(count2, int)
        self.assertEqual(count1, count2)

    @mute_logger('odoo.models')
    def test_05_immutable(self):
        """ Check that a recordset remains the same, even after updates. """
        domain = [('name', 'ilike', 'r')]
        records = self.env['test_base.model'].search(domain)
        self.assertTrue(records)
        ids = records.ids

        # modify those records, and check that records has not changed
        records.write({'active': False})
        self.assertEqual(ids, records.ids)

        # redo the search, and check that the result is now empty
        records2 = self.env['test_base.model'].search(domain)
        self.assertFalse(records2)

    @mute_logger('odoo.models')
    def test_06_fields(self):
        """ Check that relation fields return records, recordsets or nulls. """
        user = self.env.user
        self.assertIsRecord(user, 'res.users')
        self.assertIsRecord(user.partner_id, 'res.partner')
        self.assertIsRecordset(user.groups_id, 'res.groups')

        records = self.env['test_base.model'].search([])
        for name, field in records._fields.items():
            if field.type == 'many2one':
                for r in records:
                    self.assertIsRecord(r[name], field.comodel_name)
            elif field.type == 'reference':
                for r in records:
                    if r[name]:
                        self.assertIsRecord(r[name], field.comodel_name)
            elif field.type in ('one2many', 'many2many'):
                for r in records:
                    self.assertIsRecordset(r[name], field.comodel_name)

    @mute_logger('odoo.models')
    def test_07_null(self):
        """ Check behavior of null instances. """
        # select a records without a parent
        record = self.env['test_base.model'].search([('parent_id', '=', False)])[0]
        # check record and related null instances
        self.assertTrue(record)
        self.assertIsRecord(record, 'test_base.model')

        self.assertFalse(record.parent_id)
        self.assertIsNull(record.parent_id, 'test_base.model')

        self.assertIs(record.parent_id.id, False)

        self.assertFalse(record.parent_id.many2one_id)
        self.assertIsNull(record.parent_id.many2one_id, 'test_m2o_relational.model')

        self.assertFalse(record.parent_id.many2one_id.many2one_id)
        self.assertIsRecordset(record.parent_id.many2one_id.many2one_id, 'test_m2o_relational.model')

    @mute_logger('odoo.models')
    def test_40_new_new(self):
        """ Call new-style methods in the new API style. """
        records = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertTrue(records)

        # call method write on records itself, and check its effect
        records.write({'active': False})
        for r in records:
            self.assertFalse(r.active)

    @mute_logger('odoo.models')
    def test_45_new_new(self):
        """ Call new-style methods on records (new API style). """
        records = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertTrue(records)

        # call method write on partner records, and check its effects
        for r in records:
            r.write({'active': False})
        for r in records:
            self.assertFalse(r.active)

    @mute_logger('odoo.models')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_50_environment(self):
        """ Test environment on records. """
        # records and reachable records are attached to self.env
        records = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertEqual(records.env, self.env)
        for x in (records, records[0], records[0].many2one_id):
            self.assertEqual(x.env, self.env)
        for r in records:
            self.assertEqual(r.env, self.env)
        # check that the current user can read and modify data
        records[0].many2one_id.name
        records[0].many2one_id.write({'name': 'Fools'})

        # create an environment with the demo user
        demo = self.env['res.users'].search([('login', '=', 'demo')])[0]
        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        # test record and related records are still attached to self.env
        self.assertEqual(records.env, self.env)
        for x in (records, records[0], records[0].many2one_id):
            self.assertEqual(x.env, self.env)
        for p in records:
            self.assertEqual(p.env, self.env)
        # create record instances attached to demo_env
        demo_records = records.sudo(demo)
        self.assertEqual(demo_records.env, demo_env)
        for x in (demo_records, demo_records[0], demo_records[0].many2one_id):
            self.assertEqual(x.env, demo_env)
        for r in demo_records:
            self.assertEqual(r.env, demo_env)

        # demo user can read but not modify data
        demo_records[0].many2one_id.name
        with self.assertRaises(AccessError):
            demo_records[0].many2one_id.write({'name': 'Pricks'})

        # remove demo user from all groups
        demo.write({'groups_id': [(5,)]})

        # demo user can no longer access partner data
        with self.assertRaises(AccessError):
            demo_records[0].many2one_id.name

    @mute_logger('odoo.models')
    def test_55_draft(self):
        """ Test draft mode nesting. """
        env = self.env
        self.assertFalse(env.in_draft)
        with env.do_in_draft():
            self.assertTrue(env.in_draft)
            with env.do_in_draft():
                self.assertTrue(env.in_draft)
                with env.do_in_draft():
                    self.assertTrue(env.in_draft)
                self.assertTrue(env.in_draft)
            self.assertTrue(env.in_draft)
        self.assertFalse(env.in_draft)

    @mute_logger('odoo.models')
    def test_60_cache(self):
        """ Check the record cache behavior """
        TestModel = self.env['test_base.model']
        pids = []
        data = {
            'partner One': ['Partner One - One', 'Partner One - Two'],
            'Partner Two': ['Partner Two - One'],
            'Partner Three': ['Partner Three - One'],
        }
        for p in data:
            pids.append(TestModel.create({
                'name': p,
                'child_ids': [(0, 0, {'name': c}) for c in data[p]],
            }).id)

        records = TestModel.search([('id', 'in', pids)])
        record1, record2 = records[0], records[1]
        children1, children2 = record1.child_ids, record2.child_ids
        self.assertTrue(children1)
        self.assertTrue(children2)

        # take a child contact
        child = children1[0]
        self.assertEqual(child.parent_id, record1)
        self.assertIn(child, record1.child_ids)
        self.assertNotIn(child, record2.child_ids)

        # fetch data in the cache
        for r in records:
            r.name, r.many2one_id.name
        self.env.cache.check(self.env)

        # change its parent
        child.write({'parent_id': record2.id})
        self.env.cache.check(self.env)

        # check recordsets
        self.assertEqual(child.parent_id, record2)
        self.assertNotIn(child, record1.child_ids)
        self.assertIn(child, record2.child_ids)
        self.assertEqual(set(record1.child_ids + child), set(children1))
        self.assertEqual(set(record2.child_ids), set(children2 + child))
        self.env.cache.check(self.env)

        # delete it
        child.unlink()
        self.env.cache.check(self.env)

        # check recordsets
        self.assertEqual(set(record1.child_ids), set(children1) - set([child]))
        self.assertEqual(set(record2.child_ids), set(children2))
        self.env.cache.check(self.env)

        # convert from the cache format to the write format
        record = record1
        record.many2one_id, record.child_ids
        data = record._convert_to_write(record._cache)
        self.assertEqual(data['many2one_id'], record.many2one_id.id)
        self.assertEqual(data['child_ids'], [(6, 0, record.child_ids.ids)])

    @mute_logger('odoo.models')
    def test_60_prefetch(self):
        """ Check the record cache prefetching """
        records = self.env['test_base.model'].search([], limit=models.PREFETCH_MAX)
        self.assertTrue(len(records) > 1)

        # all the records in records are ready for prefetching
        self.assertItemsEqual(records.ids, records._prefetch['test_base.model'])

        # reading ONE record should fetch them ALL
        for record in records:
            record.many2one_id
            break
        record_ids_with_field = [record.id
                                  for record in records
                                  if 'many2one_id' in record._cache]
        self.assertItemsEqual(record_ids_with_field, records.ids)

        # records' states are ready for prefetching
        many2one_record_ids = {sid
                       for record in records
                       for sid in record._cache['many2one_id']}
        self.assertTrue(len(many2one_record_ids) > 1)
        self.assertItemsEqual(many2one_record_ids, records._prefetch['test_m2o_relational.model'])

        # reading ONE record should fetch ALL records relational model records
        for record in records:
            if record.many2one_id:
                record.many2one_id.name
                break
        many2one_ids_with_field = [state.id
                                  for state in records.mapped('many2one_id')
                                  if 'name' in state._cache]
        self.assertItemsEqual(many2one_ids_with_field, many2one_record_ids)

    @mute_logger('odoo.models')
    def test_60_prefetch_object(self):
        """ Check the prefetching model. """
        records = self.env['test_base.model'].search([], limit=models.PREFETCH_MAX)
        self.assertTrue(records)

        def same_prefetch(a, b):
            self.assertIs(a._prefetch, b._prefetch)
        def diff_prefetch(a, b):
            self.assertIsNot(a._prefetch, b._prefetch)

        # the recordset operations below should create new prefetch objects
        diff_prefetch(records, records.browse())
        diff_prefetch(records, records.browse(records.ids))
        diff_prefetch(records, records[0])
        diff_prefetch(records, records[:3])
        # the recordset operations below should pass the prefetch object
        same_prefetch(records, records.sudo(self.env.ref('base.user_demo')))
        same_prefetch(records, records.with_context(active_test=False))
        same_prefetch(records, records[:3].with_prefetch(records._prefetch))
        # iterating and reading relational fields should pass the prefetch object
        self.assertEqual(type(records).many2one_id.type, 'many2one')
        self.assertEqual(type(records).one2many_ids.type, 'one2many')
        self.assertEqual(type(records).many2many_ids.type, 'many2many')
        vals0 = {
            'name': 'Empty relational fields',
            'many2one_id': False,
            'many2many_ids': [],
            'one2many_ids': [],
        }
        vals1 = {
            'name': 'Non-empty relational fields',
            'many2one_id': self.ref('test_base.test_m2o_record_1'),
            'many2many_ids': [(0, 0, {'name': 'FOO42'})],
            'one2many_ids': [(4, self.ref('test_base.test_o2m_record_1'))],
        }
        records = records.create(vals0) + records.create(vals1)
        for record in records:
            same_prefetch(records, record)
            same_prefetch(records, record.many2one_id)
            same_prefetch(records, record.many2many_ids)
            same_prefetch(records, record.one2many_ids)
        # same with empty recordsets
        empty = records.browse()
        same_prefetch(empty, empty.many2one_id)
        same_prefetch(empty, empty.many2many_ids)
        same_prefetch(empty, empty.one2many_ids)

    @mute_logger('odoo.models')
    def test_60_prefetch_read(self):
        """ Check that reading a field computes it on self only. """
        Partner = self.env['res.partner']
        field = type(Partner).company_type
        self.assertTrue(field.compute and not field.store)

        partner1 = Partner.create({'name': 'Foo'})
        partner2 = Partner.create({'name': 'Bar', 'parent_id': partner1.id})
        self.assertEqual(partner1.child_ids, partner2)

        # reading partner1 should not prefetch 'company_type' on partner2
        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(['company_type'])
        self.assertIn('company_type', partner1._cache)
        self.assertNotIn('company_type', partner2._cache)

        # reading partner1 should not prefetch 'company_type' on partner2
        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(['child_ids', 'company_type'])
        self.assertIn('company_type', partner1._cache)
        self.assertNotIn('company_type', partner2._cache)

    @mute_logger('odoo.models')
    def test_70_one(self):
        """ Check method one(). """
        # check with many records
        ps = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertTrue(len(ps) > 1)
        with self.assertRaises(ValueError):
            ps.ensure_one()

        p1 = ps[0]
        self.assertEqual(len(p1), 1)
        self.assertEqual(p1.ensure_one(), p1)

        p0 = self.env['test_base.model'].browse()
        self.assertEqual(len(p0), 0)
        with self.assertRaises(ValueError):
            p0.ensure_one()

    @mute_logger('odoo.models')
    def test_80_contains(self):
        """ Test membership on recordset. """
        r1 = self.env['test_base.model'].search([('name', 'ilike', 'r')], limit=1).ensure_one()
        rs = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertTrue(r1 in rs)

    @mute_logger('odoo.models')
    def test_80_set_operations(self):
        """ Check set operations on recordsets. """
        ra = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        rb = self.env['test_base.model'].search([('name', 'ilike', 'r')])
        self.assertTrue(ra)
        self.assertTrue(rb)
        self.assertTrue(set(ra) & set(rb))

        concat = ra + rb
        self.assertEqual(list(concat), list(ra) + list(rb))
        self.assertEqual(len(concat), len(ra) + len(rb))

        difference = ra - rb
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(ra) - set(rb))
        self.assertLessEqual(difference, ra)

        intersection = ra & rb
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(ra) & set(rb))
        self.assertLessEqual(intersection, ra)
        self.assertLessEqual(intersection, rb)

        union = ra | rb
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(ra) | set(rb))
        self.assertGreaterEqual(union, ra)
        self.assertGreaterEqual(union, rb)

        # one cannot mix different models with set operations
        rs = ra
        ms = self.env['ir.ui.menu'].search([])
        self.assertNotEqual(rs._name, ms._name)
        self.assertNotEqual(rs, ms)

        with self.assertRaises(TypeError):
            res = rs + ms
        with self.assertRaises(TypeError):
            res = rs - ms
        with self.assertRaises(TypeError):
            res = rs & ms
        with self.assertRaises(TypeError):
            res = rs | ms
        with self.assertRaises(TypeError):
            res = rs < ms
        with self.assertRaises(TypeError):
            res = rs <= ms
        with self.assertRaises(TypeError):
            res = rs > ms
        with self.assertRaises(TypeError):
            res = rs >= ms

    @mute_logger('odoo.models')
    def test_80_filter(self):
        """ Check filter on recordsets. """
        rs = self.env['test_base.model'].search([])
        records = rs.browse([r.id for r in rs if r.is_boolean])

        # filter on a single field
        self.assertEqual(rs.filtered(lambda r: r.is_boolean), records)
        self.assertEqual(rs.filtered('is_boolean'), records)

        # filter on a sequence of fields
        self.assertEqual(
            rs.filtered(lambda r: r.parent_id.is_boolean),
            rs.filtered('parent_id.is_boolean')
        )

    @mute_logger('odoo.models')
    def test_80_map(self):
        """ Check map on recordsets. """
        ps = self.env['test_base.model'].search([])
        parents = ps.browse()
        for p in ps: parents |= p.parent_id

        # map a single field
        self.assertEqual(ps.mapped(lambda p: p.parent_id), parents)
        self.assertEqual(ps.mapped('parent_id'), parents)

        # map a sequence of fields
        self.assertEqual(
            ps.mapped(lambda p: p.parent_id.name),
            [p.parent_id.name for p in ps]
        )
        self.assertEqual(
            ps.mapped('parent_id.name'),
            [p.name for p in parents]
        )

        # map an empty sequence of fields
        self.assertEqual(ps.mapped(''), ps)

    @mute_logger('odoo.models')
    def test_80_sorted(self):
        """ Check sorted on recordsets. """
        ps = self.env['test_base.model'].search([])
        # sort by model order
        qs = ps[:len(ps) // 2] + ps[len(ps) // 2:]
        self.assertEqual(qs.sorted().ids, ps.ids)

        # sort by name, with a function or a field name
        by_name_ids = [p.id for p in sorted(ps, key=lambda p: p.name)]
        self.assertEqual(ps.sorted(lambda p: p.name).ids, by_name_ids)
        self.assertEqual(ps.sorted('name').ids, by_name_ids)

        # sort by inverse name, with a field name
        by_name_ids.reverse()
        self.assertEqual(ps.sorted('name', reverse=True).ids, by_name_ids)
