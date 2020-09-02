# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import mock
from collections import defaultdict
import json

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tools import pycompat, json_default


class TestPerformance(TransactionCase):

    def setUp(self):
        super(TestPerformance, self).setUp()
        for record in self.env['test_performance.base'].search([]):
            # create 10 line with 10 tags
            for val in range(10):
                self.env['test_performance.line'].create({
                    'base_id': record.id,
                    'value': val,
                    'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
                })

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
    def test_multi_level_relation_preftech(self):
        """ Test recursive prefetch """
        records = self.env['test_performance.base'].search([])
        Tag = self.env["test_performance.tag"]
        self.assertEqual(len(records), 5)

        # without cache
        with self.assertQueryCount(__system__=6, demo=6):
            for record in records:
                for line in record.line_ids:
                    for tag in line.tag_ids:
                        tag.name

        # with cache
        with self.assertQueryCount(0):
            for record in records:
                for line in record.line_ids:
                    for tag in line.tag_ids:
                        tag.name

    @users('__system__', 'demo')
    @warmup
    def test_filtered_relation_preftech(self):
        """ Test prefetch on filtered records"""
        records = self.env['test_performance.base'].search([])
        Line = self.env["test_performance.line"]
        self.assertEqual(len(records), 5)

        # ensure that values are in cache for line ids and filter records
        records.mapped("line_ids")
        filtered = records.filtered(lambda a: True)

        with mock.patch.object(Line.__class__, '_compute_computed_value') as mocked_compute:
            for record in filtered:
                for line in record.line_ids:
                    line.computed_value
            self.assertEquals(mocked_compute.call_count, 1)


    @users('__system__', 'demo')
    @warmup
    def test_filtered_multi_level_relation_preftech(self):
        """ Test recursive prefetch on filtered records"""
        records = self.env['test_performance.base'].search([])
        Tag = self.env["test_performance.tag"]
        self.assertEqual(len(records), 5)

        # ensure that values are in cache for tag ids and filter records
        records.mapped("line_ids.tag_ids")
        filtered = records.filtered(lambda a: True)

        with mock.patch.object(Tag.__class__, '_compute_computed_name') as mocked_compute:
            for record in filtered:
                for line in record.line_ids:
                    for tag in line.tag_ids:
                        tag.computed_name
        self.assertEquals(mocked_compute.call_count, 1)


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

        with self.assertQueryCount(__system__=3, demo=3):
            records.write({'value': 42})

    @users('__system__', 'demo')
    @warmup
    def test_create_base(self):
        """ Create records. """
        with self.assertQueryCount(__system__=6, demo=6):
            self.env['test_performance.base'].create({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        with self.assertQueryCount(__system__=20, demo=20):
            self.env['test_performance.base'].create({
                'name': 'X',
                'line_ids': [(0, 0, {'value': val}) for val in range(10)],
            })

    @users('__system__', 'demo')
    @warmup
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        with self.assertQueryCount(__system__=17, demo=17):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
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
            with self.env.do_in_onchange():
                records.mapped('value')
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
            for res, exp in pycompat.izip(result, expected):
                self.assertEqual(res['__domain'], exp['__domain'])
                self.assertEqual(res['partner_id'][0], exp['partner_id'][0])
                self.assertEqual(res['partner_id_count'], exp['partner_id_count'])
                self.assertEqual(res['value'], exp['value'])
        # now serialize to json, which should force evaluation
        with self.assertQueryCount(__system__=1, demo=1):
            json.dumps(result, default=json_default)
