import unittest2

import openerp
from openerp.tests import common
from datetime import date

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID


def registry(model):
    return openerp.modules.registry.RegistryManager.get(DB)[model]


def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).cursor()


def drop_sequence(code):
    cr = cursor()
    try:
        s = registry('ir.sequence')
        ids = s.search(cr, ADMIN_USER_ID, [('code', '=', code)])
        s.unlink(cr, ADMIN_USER_ID, ids)
        cr.commit()
    finally:
        cr.close()


class test_ir_sequence_date_range_standard(unittest2.TestCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object with date ranges enabled. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_date_range', name='Test sequence', use_date_range=True)
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        cr = cursor()
        try:
            year = str(int(date.today().strftime("%Y")) - 1)
            dt = "{}-01-16".format(year)
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range', {'ir_sequence_date': dt})
            self.assertEqual(n, '1')
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range', {'ir_sequence_date': dt})
            self.assertEqual(n, '2')
            # modify the range of date created
            domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', '{}-01-01'.format(year))]
            seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
            registry('ir.sequence.date_range').write(cr, ADMIN_USER_ID, seq_date_range_id, {'date_from': '{}-01-18'.format(year)}, {})
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range', {'ir_sequence_date': dt})
            self.assertEqual(n, '1')
            # check the newly created sequence stops at the 17th of January
            domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', '{}-01-01'.format(year))]
            seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
            seq_date_range = registry('ir.sequence.date_range').browse(cr, ADMIN_USER_ID, seq_date_range_id[0])
            self.assertEqual(seq_date_range.date_to, '{}-01-17'.format(year))
            cr.commit()
        finally:
            cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_date_range')


class test_ir_sequence_date_range_no_gap(unittest2.TestCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_date_range_1_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_date_range_2', name='Test sequence',
                     implementation='no_gap', use_date_range=True)
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        cr = cursor()
        try:
            year = str(int(date.today().strftime("%Y")) - 1)
            dt = "{}-01-16".format(year)
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
            self.assertEqual(n, '1')
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
            self.assertEqual(n, '2')
            # modify the range of date created
            domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', '{}-01-01'.format(year))]
            seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
            registry('ir.sequence.date_range').write(cr, ADMIN_USER_ID, seq_date_range_id, {'date_from': '{}-01-18'.format(year)}, {})
            n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
            self.assertEqual(n, '1')
            # check the newly created sequence stops at the 17th of January
            domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', '{}-01-01'.format(year))]
            seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
            seq_date_range = registry('ir.sequence.date_range').browse(cr, ADMIN_USER_ID, seq_date_range_id[0])
            self.assertEqual(seq_date_range.date_to, '{}-01-17'.format(year))
            cr.commit()
        finally:
            cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_date_range_2')


class test_ir_sequence_date_range_change_implementation(unittest2.TestCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_date_range_3', name='Test sequence', use_date_range=True)
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            d = {
                'code': 'test_sequence_date_range_4',
                'name': 'Test sequence',
                'implementation': 'no_gap',
                'use_date_range': True
            }
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_date_range_2_use(self):
        """ Make some use of the sequences to create some subsequences """
        cr = cursor()
        try:
            year = str(int(date.today().strftime("%Y")) - 1)
            dt = "{}-01-16".format(year)
            f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_3', {})
            assert all(str(x) == f() for x in xrange(1, 5))
            f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_3', {'ir_sequence_date': dt})
            assert all(str(x) == f() for x in xrange(1, 5))
            f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_4', {})
            assert all(str(x) == f() for x in xrange(1, 5))
            f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_date_range_4', {'ir_sequence_date': dt})
            assert all(str(x) == f() for x in xrange(1, 5))
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_date_range_3_write(self):
        """swap the implementation method on both"""
        cr = cursor()
        try:
            ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [
                ('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])
            ], {})
            registry('ir.sequence').write(cr, ADMIN_USER_ID, ids, {'implementation': 'standard'})
            registry('ir.sequence').write(cr, ADMIN_USER_ID, ids, {'implementation': 'no_gap'})
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_date_range_3_unlink(self):
        cr = cursor()
        try:
            ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [
                ('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])
            ], {})
            registry('ir.sequence').unlink(cr, ADMIN_USER_ID, ids, {})
            cr.commit()
        finally:
            cr.close()


if __name__ == '__main__':
    unittest2.main()
