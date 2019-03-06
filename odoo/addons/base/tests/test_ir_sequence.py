# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
import unittest

import psycopg2
import psycopg2.errorcodes

import odoo
from odoo.tests import common

ADMIN_USER_ID = common.ADMIN_USER_ID

@contextmanager
def environment():
    """ Return an environment with a new cursor for the current database; the
        cursor is committed and closed after the context block.
    """
    registry = odoo.registry(common.get_db_name())
    with registry.cursor() as cr:
        yield odoo.api.Environment(cr, ADMIN_USER_ID, {})


def drop_sequence(code):
    with environment() as env:
        seq = env['ir.sequence'].search([('code', '=', code)])
        seq.unlink()


@common.tagged('standard', 'at_install')
class TestIrSequenceStandard(unittest.TestCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        with environment() as env:
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type',
                'name': 'Test sequence',
            })
            self.assertTrue(seq)

    def test_ir_sequence_search(self):
        """ Try a search. """
        with environment() as env:
            seqs = env['ir.sequence'].search([])
            self.assertTrue(seqs)

    def test_ir_sequence_draw(self):
        """ Try to draw a number. """
        with environment() as env:
            n = env['ir.sequence'].next_by_code('test_sequence_type')
            self.assertTrue(n)

    def test_ir_sequence_draw_twice(self):
        """ Try to draw a number from two transactions. """
        with environment() as env0:
            with environment() as env1:
                n0 = env0['ir.sequence'].next_by_code('test_sequence_type')
                self.assertTrue(n0)
                n1 = env1['ir.sequence'].next_by_code('test_sequence_type')
                self.assertTrue(n1)

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type')


@common.tagged('standard', 'at_install')
class TestIrSequenceNoGap(unittest.TestCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_create_no_gap(self):
        """ Try to create a sequence object. """
        with environment() as env:
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type_2',
                'name': 'Test sequence',
                'implementation': 'no_gap',
            })
            self.assertTrue(seq)

    def test_ir_sequence_draw_no_gap(self):
        """ Try to draw a number. """
        with environment() as env:
            n = env['ir.sequence'].next_by_code('test_sequence_type_2')
            self.assertTrue(n)

    def test_ir_sequence_draw_twice_no_gap(self):
        """ Try to draw a number from two transactions.
        This is expected to not work.
        """
        with environment() as env0:
            with environment() as env1:
                env1.cr._default_log_exceptions = False # Prevent logging a traceback
                with self.assertRaises(psycopg2.OperationalError) as e:
                    n0 = env0['ir.sequence'].next_by_code('test_sequence_type_2')
                    self.assertTrue(n0)
                    n1 = env1['ir.sequence'].next_by_code('test_sequence_type_2')
                self.assertEqual(e.exception.pgcode, psycopg2.errorcodes.LOCK_NOT_AVAILABLE, msg="postgresql returned an incorrect errcode")

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_2')


@common.tagged('standard', 'at_install')
class TestIrSequenceChangeImplementation(unittest.TestCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_1_create(self):
        """ Try to create a sequence object. """
        with environment() as env:
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type_3',
                'name': 'Test sequence',
            })
            self.assertTrue(seq)
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type_4',
                'name': 'Test sequence',
                'implementation': 'no_gap',
            })
            self.assertTrue(seq)

    def test_ir_sequence_2_write(self):
        with environment() as env:
            domain = [('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])]
            seqs = env['ir.sequence'].search(domain)
            seqs.write({'implementation': 'standard'})
            seqs.write({'implementation': 'no_gap'})

    def test_ir_sequence_3_unlink(self):
        with environment() as env:
            domain = [('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])]
            seqs = env['ir.sequence'].search(domain)
            seqs.unlink()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_3')
        drop_sequence('test_sequence_type_4')


@common.tagged('standard', 'at_install')
class TestIrSequenceGenerate(unittest.TestCase):
    """ Create sequence objects and generate some values. """

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        with environment() as env:
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type_5',
                'name': 'Test sequence',
            })
            self.assertTrue(seq)

        with environment() as env:
            for i in range(1, 10):
                n = env['ir.sequence'].next_by_code('test_sequence_type_5')
                self.assertEqual(n, str(i))

    def test_ir_sequence_create_no_gap(self):
        """ Try to create a sequence object. """
        with environment() as env:
            seq = env['ir.sequence'].create({
                'code': 'test_sequence_type_6',
                'name': 'Test sequence',
                'implementation': 'no_gap',
            })
            self.assertTrue(seq)

        with environment() as env:
            for i in range(1, 10):
                n = env['ir.sequence'].next_by_code('test_sequence_type_6')
                self.assertEqual(n, str(i))

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_5')
        drop_sequence('test_sequence_type_6')


class TestIrSequenceInit(common.TransactionCase):

    def test_00(self):
        """ test whether the read method returns the right number_next value
            (from postgreSQL sequence and not ir_sequence value)
        """
        # first creation of sequence (normal)
        seq = self.env['ir.sequence'].create({
            'number_next': 1,
            'company_id': 1,
            'padding': 4,
            'number_increment': 1,
            'implementation': 'standard',
            'name': 'test-sequence-00',
        })
        # Call next() 4 times, and check the last returned value
        seq.next_by_id()
        seq.next_by_id()
        seq.next_by_id()
        n = seq.next_by_id()
        self.assertEqual(n, "0004", 'The actual sequence value must be 4. reading : %s' % n)
        # reset sequence to 1 by write()
        seq.write({'number_next': 1})
        # Read the value of the current sequence
        n = seq.next_by_id()
        self.assertEqual(n, "0001", 'The actual sequence value must be 1. reading : %s' % n)
