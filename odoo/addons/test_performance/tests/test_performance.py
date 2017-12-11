# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users


class TestPerformance(TransactionCase):

    @users('admin', 'demo')
    def test_read_base(self):
        """ Read records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.mapped('partner_id.country_id.name')
        self.env.cache.invalidate()

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
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.write({'name': 'X'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=1, demo=1):
            records.write({'name': 'Y'})

    @users('admin', 'demo')
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.write({'value': 21})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=3, demo=3):
            records.write({'value': 42})

    @users('admin', 'demo')
    def test_create_base(self):
        """ Create records. """
        model = self.env['test_performance.base']

        # warm up ormcache
        model.create({'name': 'X'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=6, demo=6):
            model.create({'name': 'Y'})

    @users('admin', 'demo')
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        model = self.env['test_performance.base']
        values = {
            'name': 'X',
            'line_ids': [(0, 0, {'value': val}) for val in range(10)],
        }

        # warm up ormcache
        model.create(values)
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=38, demo=38):
            model.create(values)

    @users('admin', 'demo')
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        model = self.env['test_performance.base']
        values = {
            'name': 'X',
            'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
        }

        # warm up ormcache
        model.create(values)
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=17, demo=17):
            model.create(values)
