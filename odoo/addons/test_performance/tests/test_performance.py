# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, PerformanceCase, queryCount


class TestPerformance(TransactionCase, PerformanceCase):

    @queryCount(admin=3, demo=3)
    def test_read_base(self):
        """ Read records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.startQueryCount()

        # without cache
        for record in records:
            record.partner_id.country_id.name

        # with cache
        for record in records:
            record.partner_id.country_id.name

        # value_pc must have been prefetched, too
        for record in records:
            record.value_pc

    @queryCount(admin=1, demo=1)
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.startQueryCount()

        records.write({'name': self.str('X')})

    @queryCount(admin=3, demo=3)
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.startQueryCount()

        records.write({'value': self.int(20)})

    @queryCount(admin=6, demo=6)
    def test_create_base(self):
        """ Create records. """
        model = self.env['test_performance.base']
        model.create({'name': self.str('X')})

    @queryCount(admin=38, demo=38)
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        model = self.env['test_performance.base']
        model.create({
            'name': self.str('Y'),
            'line_ids': [(0, 0, {'value': val}) for val in range(10)],
        })

    @queryCount(admin=17, demo=17)
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        model = self.env['test_performance.base']
        model.create({
            'name': self.str('X'),
            'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
        })
