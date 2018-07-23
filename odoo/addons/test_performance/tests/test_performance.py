# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tools import pycompat


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
            json.dumps(result)
