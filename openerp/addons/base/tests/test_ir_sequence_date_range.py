# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import SingleTransactionCase
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class TestIrSequenceDateRangeStandard(SingleTransactionCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object with date ranges enabled. """
        seq = self.env['ir.sequence'].create({
            'code': 'test_sequence_date_range',
            'name': 'Test sequence',
            'use_date_range': True,
        })
        self.assertTrue(seq)

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        year = date.today().year - 1
        january = lambda d: date(year, 1, d).strftime(DATE_FORMAT)

        seq16 = self.env['ir.sequence'].with_context({'ir_sequence_date': january(16)})
        n = seq16.next_by_code('test_sequence_date_range')
        self.assertEqual(n, '1')
        n = seq16.next_by_code('test_sequence_date_range')
        self.assertEqual(n, '2')

        # modify the range of date created
        domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', january(1))]
        seq_date_range = self.env['ir.sequence.date_range'].search(domain)
        seq_date_range.write({'date_from': january(18)})
        n = seq16.next_by_code('test_sequence_date_range')
        self.assertEqual(n, '1')

        # check the newly created sequence stops at the 17th of January
        domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', january(1))]
        seq_date_range = self.env['ir.sequence.date_range'].search(domain)
        self.assertEqual(seq_date_range.date_to, january(17))

    def test_ir_sequence_date_range_3_unlink(self):
        seq = self.env['ir.sequence'].search([('code', '=', 'test_sequence_date_range')])
        seq.unlink()


class TestIrSequenceDateRangeNoGap(SingleTransactionCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_date_range_1_create_no_gap(self):
        """ Try to create a sequence object. """
        seq = self.env['ir.sequence'].create({
            'code': 'test_sequence_date_range_2',
            'name': 'Test sequence',
            'use_date_range': True,
            'implementation': 'no_gap',
        })
        self.assertTrue(seq)

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        year = date.today().year - 1
        january = lambda d: date(year, 1, d).strftime(DATE_FORMAT)

        seq16 = self.env['ir.sequence'].with_context({'ir_sequence_date': january(16)})
        n = seq16.next_by_code('test_sequence_date_range_2')
        self.assertEqual(n, '1')
        n = seq16.next_by_code('test_sequence_date_range_2')
        self.assertEqual(n, '2')

        # modify the range of date created
        domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', january(1))]
        seq_date_range = self.env['ir.sequence.date_range'].search(domain)
        seq_date_range.write({'date_from': january(18)})
        n = seq16.next_by_code('test_sequence_date_range_2')
        self.assertEqual(n, '1')

        # check the newly created sequence stops at the 17th of January
        domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', january(1))]
        seq_date_range = self.env['ir.sequence.date_range'].search(domain)
        self.assertEqual(seq_date_range.date_to, january(17))

    def test_ir_sequence_date_range_3_unlink(self):
        seq = self.env['ir.sequence'].search([('code', '=', 'test_sequence_date_range_2')])
        seq.unlink()


class TestIrSequenceDateRangeChangeImplementation(SingleTransactionCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object. """
        seq = self.env['ir.sequence'].create({
            'code': 'test_sequence_date_range_3',
            'name': 'Test sequence',
            'use_date_range': True,
        })
        self.assertTrue(seq)

        seq = self.env['ir.sequence'].create({
            'code': 'test_sequence_date_range_4',
            'name': 'Test sequence',
            'use_date_range': True,
            'implementation': 'no_gap',
        })
        self.assertTrue(seq)

    def test_ir_sequence_date_range_2_use(self):
        """ Make some use of the sequences to create some subsequences """
        year = date.today().year - 1
        january = lambda d: date(year, 1, d).strftime(DATE_FORMAT)

        seq = self.env['ir.sequence']
        seq16 = self.env['ir.sequence'].with_context({'ir_sequence_date': january(16)})

        for i in xrange(1, 5):
            n = seq.next_by_code('test_sequence_date_range_3')
            self.assertEqual(n, str(i))
        for i in xrange(1, 5):
            n = seq16.next_by_code('test_sequence_date_range_3')
            self.assertEqual(n, str(i))
        for i in xrange(1, 5):
            n = seq.next_by_code('test_sequence_date_range_4')
            self.assertEqual(n, str(i))
        for i in xrange(1, 5):
            n = seq16.next_by_code('test_sequence_date_range_4')
            self.assertEqual(n, str(i))

    def test_ir_sequence_date_range_3_write(self):
        """swap the implementation method on both"""
        domain = [('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])]
        seqs = self.env['ir.sequence'].search(domain)
        seqs.write({'implementation': 'standard'})
        seqs.write({'implementation': 'no_gap'})

    def test_ir_sequence_date_range_4_unlink(self):
        domain = [('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])]
        seqs = self.env['ir.sequence'].search(domain)
        seqs.unlink()
