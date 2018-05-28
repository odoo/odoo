# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users, warmup


class TestPerformance(TransactionCase):

    @users('admin', 'demo')
    @warmup
    def test_read_base(self):
        """ Read records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=3, demo=3):
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

    @users('admin', 'demo')
    @warmup
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=1, demo=1):
            records.write({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=3, demo=3):
            records.write({'value': 42})

    @users('admin', 'demo')
    @warmup
    def test_create_base(self):
        """ Create records. """
        with self.assertQueryCount(admin=6, demo=6):
            self.env['test_performance.base'].create({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        with self.assertQueryCount(admin=38, demo=38):
            self.env['test_performance.base'].create({
                'name': 'X',
                'line_ids': [(0, 0, {'value': val}) for val in range(10)],
            })

    @users('admin', 'demo')
    @warmup
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        with self.assertQueryCount(admin=17, demo=17):
            self.env['test_performance.base'].create({
                'name': 'X',
                'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
            })

    @users('admin', 'demo')
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
        with self.assertQueryCount(admin=2, demo=2):
            records.mapped('value')
        records.invalidate_cache(['value'])

        with self.assertQueryCount(admin=2, demo=2):
            with self.env.do_in_onchange():
                records.mapped('value')
        self.env.cr.execute(
            'delete from test_performance_base where id not in %s',
            (tuple(initial_records.ids),)
        )
