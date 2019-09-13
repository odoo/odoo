# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json

from odoo.tests.common import TransactionCase, users, warmup, tagged
from odoo.tools import mute_logger


class TestPerformance(TransactionCase):

    @users('__system__', 'demo')
    @warmup
    def test_read_base(self):
        """ Read records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=3, demo=3):
            # without cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # with cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # value_pc must have been prefetched, too
            for record in records:
                record.value_pc

    @users('__system__', 'demo')
    @warmup
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=1, demo=1):
            records.write({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=1, demo=1):
            records.write({'value': 42})

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'demo')
    @warmup
    def test_write_base_one2many(self):
        """ Write on one2many field. """
        rec1 = self.env['test_performance.base'].create({'name': 'X'})

        # create N lines on rec1: O(N) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(4):
            rec1.write({'line_ids': [(0, 0, {'value': 0})]})
        self.assertEqual(len(rec1.line_ids), 1)

        rec1.invalidate_cache()
        with self.assertQueryCount(17):
            rec1.write({'line_ids': [(0, 0, {'value': val}) for val in range(1, 12)]})
        self.assertEqual(len(rec1.line_ids), 12)

        lines = rec1.line_ids

        # update N lines: O(N) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(8):
            rec1.write({'line_ids': [(1, line.id, {'value': 42}) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines)

        rec1.invalidate_cache()
        with self.assertQueryCount(28):
            rec1.write({'line_ids': [(1, line.id, {'value': 42 + line.id}) for line in lines[1:]]})
        self.assertEqual(rec1.line_ids, lines)

        # delete N lines: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=18, demo=18):
            rec1.write({'line_ids': [(2, line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])

        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=16, demo=16):
            rec1.write({'line_ids': [(2, line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertFalse(lines.exists())

        rec1.write({'line_ids': [(0, 0, {'value': val}) for val in range(12)]})
        lines = rec1.line_ids

        # unlink N lines: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=14, demo=14):
            rec1.write({'line_ids': [(3, line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])

        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=16, demo=16):
            rec1.write({'line_ids': [(3, line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertFalse(lines.exists())

        rec1.write({'line_ids': [(0, 0, {'value': val}) for val in range(12)]})
        lines = rec1.line_ids
        rec2 = self.env['test_performance.base'].create({'name': 'X'})

        # link N lines from rec1 to rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(7):
            rec2.write({'line_ids': [(4, line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])
        self.assertEqual(rec2.line_ids, lines[0])

        rec1.invalidate_cache()
        with self.assertQueryCount(10):
            rec2.write({'line_ids': [(4, line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertEqual(rec2.line_ids, lines)

        rec1.invalidate_cache()
        with self.assertQueryCount(7):
            rec2.write({'line_ids': [(4, line.id) for line in lines[0]]})
        self.assertEqual(rec2.line_ids, lines)

        rec1.invalidate_cache()
        with self.assertQueryCount(7):
            rec2.write({'line_ids': [(4, line.id) for line in lines[1:]]})
        self.assertEqual(rec2.line_ids, lines)

        # empty N lines in rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=17, demo=17):
            rec2.write({'line_ids': [(5,)]})
        self.assertFalse(rec2.line_ids)

        rec1.invalidate_cache()
        with self.assertQueryCount(5):
            rec2.write({'line_ids': [(5,)]})
        self.assertFalse(rec2.line_ids)

        rec1.write({'line_ids': [(0, 0, {'value': val}) for val in range(12)]})
        lines = rec1.line_ids

        # set N lines in rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(8):
            rec2.write({'line_ids': [(6, 0, lines[0].ids)]})
        self.assertEqual(rec1.line_ids, lines[1:])
        self.assertEqual(rec2.line_ids, lines[0])

        with self.assertQueryCount(9):
            rec2.write({'line_ids': [(6, 0, lines.ids)]})
        self.assertFalse(rec1.line_ids)
        self.assertEqual(rec2.line_ids, lines)

        with self.assertQueryCount(4):
            rec2.write({'line_ids': [(6, 0, lines.ids)]})
        self.assertEqual(rec2.line_ids, lines)

    @mute_logger('odoo.models.unlink')
    def test_write_base_one2many_with_constraint(self):
        """ Write on one2many field with lines being deleted and created. """
        rec = self.env['test_performance.base'].create({'name': 'Y'})
        rec.write({'line_ids': [(0, 0, {'value': val}) for val in range(12)]})

        # This write() will raise because of the unique index if the unlink() is
        # not performed before the create()
        rec.write({'line_ids': [(5,)] + [(0, 0, {'value': val}) for val in range(6)]})
        self.assertEquals(len(rec.line_ids), 6)

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'demo')
    @warmup
    def test_write_base_many2many(self):
        """ Write on many2many field. """
        rec1 = self.env['test_performance.base'].create({'name': 'X'})

        # create N tags on rec1: O(N) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(4):
            rec1.write({'tag_ids': [(0, 0, {'name': 0})]})
        self.assertEqual(len(rec1.tag_ids), 1)

        rec1.invalidate_cache()
        with self.assertQueryCount(14):
            rec1.write({'tag_ids': [(0, 0, {'name': val}) for val in range(1, 12)]})
        self.assertEqual(len(rec1.tag_ids), 12)

        tags = rec1.tag_ids

        # update N tags: O(N) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec1.write({'tag_ids': [(1, tag.id, {'name': 'X'}) for tag in tags[0]]})
        self.assertEqual(rec1.tag_ids, tags)

        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec1.write({'tag_ids': [(1, tag.id, {'name': 'X'}) for tag in tags[1:]]})
        self.assertEqual(rec1.tag_ids, tags)

        # delete N tags: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=10, demo=10):
            rec1.write({'tag_ids': [(2, tag.id) for tag in tags[0]]})
        self.assertEqual(rec1.tag_ids, tags[1:])

        rec1.invalidate_cache()
        with self.assertQueryCount(__system__=10, demo=10):
            rec1.write({'tag_ids': [(2, tag.id) for tag in tags[1:]]})
        self.assertFalse(rec1.tag_ids)
        self.assertFalse(tags.exists())

        rec1.write({'tag_ids': [(0, 0, {'name': val}) for val in range(12)]})
        tags = rec1.tag_ids

        # unlink N tags: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec1.write({'tag_ids': [(3, tag.id) for tag in tags[0]]})
        self.assertEqual(rec1.tag_ids, tags[1:])

        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec1.write({'tag_ids': [(3, tag.id) for tag in tags[1:]]})
        self.assertFalse(rec1.tag_ids)
        self.assertTrue(tags.exists())

        rec2 = self.env['test_performance.base'].create({'name': 'X'})

        # link N tags from rec1 to rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(4, tag.id) for tag in tags[0]]})
        self.assertEqual(rec2.tag_ids, tags[0])

        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(4, tag.id) for tag in tags[1:]]})
        self.assertEqual(rec2.tag_ids, tags)

        rec1.invalidate_cache()
        with self.assertQueryCount(2):
            rec2.write({'tag_ids': [(4, tag.id) for tag in tags[1:]]})
        self.assertEqual(rec2.tag_ids, tags)

        # empty N tags in rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(5,)]})
        self.assertFalse(rec2.tag_ids)
        self.assertTrue(tags.exists())

        rec1.invalidate_cache()
        with self.assertQueryCount(2):
            rec2.write({'tag_ids': [(5,)]})
        self.assertFalse(rec2.tag_ids)

        # set N tags in rec2: O(1) queries
        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(6, 0, tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(6, 0, tags[:8].ids)]})
        self.assertEqual(rec2.tag_ids, tags[:8])

        rec1.invalidate_cache()
        with self.assertQueryCount(4):
            rec2.write({'tag_ids': [(6, 0, tags[4:].ids)]})
        self.assertEqual(rec2.tag_ids, tags[4:])

        rec1.invalidate_cache()
        with self.assertQueryCount(3):
            rec2.write({'tag_ids': [(6, 0, tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

        rec1.invalidate_cache()
        with self.assertQueryCount(2):
            rec2.write({'tag_ids': [(6, 0, tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

    @users('__system__', 'demo')
    @warmup
    def test_create_base(self):
        """ Create records. """
        with self.assertQueryCount(__system__=2, demo=2):
            self.env['test_performance.base'].create({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        with self.assertQueryCount(__system__=12, demo=12):
            self.env['test_performance.base'].create({
                'name': 'X',
                'line_ids': [(0, 0, {'value': val}) for val in range(10)],
            })

    @users('__system__', 'demo')
    @warmup
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        with self.assertQueryCount(2):
            self.env['test_performance.base'].create({'name': 'X'})

        # create N tags: add O(N) queries
        with self.assertQueryCount(13):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
            })

        # link N tags: add O(1) queries
        tags = self.env['test_performance.tag'].create([{'name': val} for val in range(10)])

        with self.assertQueryCount(3):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(4, tag.id) for tag in tags],
            })

        with self.assertQueryCount(2):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(6, 0, [])],
            })

        with self.assertQueryCount(3):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(6, 0, tags.ids)],
            })

    @users('__system__', 'demo')
    @warmup
    def test_several_prefetch(self):
        initial_records = self.env['test_performance.base'].search([])
        self.assertEqual(len(initial_records), 5)
        for _i in range(8):
            self.env.cr.execute(
                'insert into test_performance_base(value) select value from test_performance_base'
            )
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 1280)

        # should only cause 2 queries thanks to prefetching
        with self.assertQueryCount(__system__=2, demo=2):
            records.mapped('value')

        records.invalidate_cache(['value'])
        with self.assertQueryCount(__system__=2, demo=2):
            records.mapped('value')

        records.invalidate_cache(['value'])
        with self.assertQueryCount(__system__=2, demo=2):
            new_recs = records.browse(records.new(origin=record).id for record in records)
            new_recs.mapped('value')

        # clean up after each pass
        self.env.cr.execute(
            'delete from test_performance_base where id not in %s',
            (tuple(initial_records.ids),)
        )

    def expected_read_group(self):
        groups = defaultdict(list)
        for record in self.env['test_performance.base'].search([]):
            groups[record.partner_id.id].append(record.value)
        partners = self.env['res.partner'].search([('id', 'in', list(groups))])
        return [{
            '__domain': [('partner_id', '=', partner.id)],
            'partner_id': (partner.id, partner.display_name),
            'partner_id_count': len(groups[partner.id]),
            'value': sum(groups[partner.id]),
        } for partner in partners]

    @users('__system__', 'demo')
    def test_read_group_with_name_get(self):
        model = self.env['test_performance.base']
        expected = self.expected_read_group()
        # use read_group and check the expected result
        with self.assertQueryCount(__system__=2, demo=2):
            model.invalidate_cache()
            result = model.read_group([], ['partner_id', 'value'], ['partner_id'])
            self.assertEqual(result, expected)

    @users('__system__', 'demo')
    def test_read_group_without_name_get(self):
        model = self.env['test_performance.base']
        expected = self.expected_read_group()
        # use read_group and check the expected result
        with self.assertQueryCount(__system__=1, demo=1):
            model.invalidate_cache()
            result = model.read_group([], ['partner_id', 'value'], ['partner_id'])
            self.assertEqual(len(result), len(expected))
            for res, exp in zip(result, expected):
                self.assertEqual(res['__domain'], exp['__domain'])
                self.assertEqual(res['partner_id'][0], exp['partner_id'][0])
                self.assertEqual(res['partner_id_count'], exp['partner_id_count'])
                self.assertEqual(res['value'], exp['value'])
        # now serialize to json, which should force evaluation
        with self.assertQueryCount(__system__=1, demo=1):
            json.dumps(result)


@tagged('bacon_and_eggs')
class TestIrPropertyOptimizations(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Bacon = self.env['test_performance.bacon']
        self.Eggs = self.env['test_performance.eggs']

    def test_with_falsy_default(self):
        self.assertFalse(self.env['ir.property'].get('property_eggs', 'test_performance.bacon'))

        # warmup
        eggs = self.Eggs.create({})
        self.Bacon.create({})
        self.Bacon.create({'property_eggs': eggs.id})

        # create with default value
        with self.assertQueryCount(1):
            self.Bacon.create({})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=False).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({'property_eggs': False})

        # create with another value
        with self.assertQueryCount(5):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(5):
            self.Bacon.create({'property_eggs': eggs.id})

    def test_with_truthy_default(self):
        eggs = self.Eggs.create({})
        field = self.env['ir.model.fields']._get('test_performance.bacon', 'property_eggs')
        self.env['ir.property'].create({
            'name': 'property_eggs_with_bacon',
            'fields_id': field.id,
            'value': eggs,
        })

        self.assertEqual(eggs, self.env['ir.property'].get('property_eggs', 'test_performance.bacon'))

        # warmup
        self.Bacon.create({})

        # create with default value
        with self.assertQueryCount(1):
            self.Bacon.create({})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({'property_eggs': eggs.id})

        # create with another value
        eggs = self.Eggs.create({})
        self.Bacon.create({'property_eggs': eggs.id})

        with self.assertQueryCount(5):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(5):
            self.Bacon.create({'property_eggs': eggs.id})

        with self.assertQueryCount(5):
            self.Bacon.with_context(default_property_eggs=False).create({})

        with self.assertQueryCount(5):
            self.Bacon.create({'property_eggs': False})
