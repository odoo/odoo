# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence_date_range.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence_date_range.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence_date_range
# This assume an existing database.
import psycopg2
import psycopg2.errorcodes
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
    for model in ['ir.sequence', 'ir.sequence.type']:
        s = registry(model)
        ids = s.search(cr, ADMIN_USER_ID, [('code', '=', code)])
        s.unlink(cr, ADMIN_USER_ID, ids)
    cr.commit()
    cr.close()


class test_ir_sequence_date_range_standard(unittest2.TestCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object with date ranges enabled. """
        cr = cursor()
        d = dict(code='test_sequence_type', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type', name='Test sequence', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Try to draw a number to create a first subsequence then change its date range. Then, try to draw a new number. """
        cr = cursor()
        year = str(int(date.today().strftime("%Y")) - 1)
        dt = "{}-01-16".format(year)
        n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type', {'date': dt})
        self.assertEqual(n, '1')
        seq_id = registry('ir.sequence').search(cr, ADMIN_USER_ID, [['code', '=', 'test_sequence_type']], {})
        seq_date_range_ids = registry('ir.sequence').browse(cr, ADMIN_USER_ID, seq_id, {}).date_range_ids
        domain = [['id', 'in', seq_date_range_ids.ids], ['date_from', '=', '{}-01-01'.format(year)]]
        seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
        registry('ir.sequence.date_range').write(cr, ADMIN_USER_ID, seq_date_range_id, {'date_to': '{}-01-14'.format(year)}, {})
        n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type', {'date': dt})
        self.assertEqual(n, '1')
        cr.commit()
        cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type')


class test_ir_sequence_date_range_no_gap(unittest2.TestCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_date_range_1_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_2', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_2', name='Test sequence',
                 implementation='no_gap', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Try to draw a number. """
        cr = cursor()
        year = str(int(date.today().strftime("%Y")) - 1)
        dt = "{}-01-16".format(year)
        n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type_2', {'date': dt})
        self.assertEqual(n, '1')
        seq_id = registry('ir.sequence').search(cr, ADMIN_USER_ID, [['code', '=', 'test_sequence_type_2']], {})
        seq_date_range_ids = registry('ir.sequence').browse(cr, ADMIN_USER_ID, seq_id, {}).date_range_ids
        domain = [['id', 'in', seq_date_range_ids.ids], ['date_from', '=', '{}-01-01'.format(year)]]
        seq_date_range_id = registry('ir.sequence.date_range').search(cr, ADMIN_USER_ID, domain, {})
        registry('ir.sequence.date_range').write(cr, ADMIN_USER_ID, seq_date_range_id, {'date_to': '{}-01-14'.format(year)}, {})
        n = registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type_2', {'date': dt})
        self.assertEqual(n, '1')
        cr.commit()
        cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_2')


class test_ir_sequence_date_range_change_implementation(unittest2.TestCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_3', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_3', name='Test sequence', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_4', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_4', name='Test sequence',
                 implementation='no_gap', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_date_range_2_write(self):
        cr = cursor()
        ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [
            ('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])
        ], {})
        registry('ir.sequence').write(cr, ADMIN_USER_ID, ids,
                                      {'implementation': 'standard'}, {})
        registry('ir.sequence').write(cr, ADMIN_USER_ID, ids,
                                      {'implementation': 'no_gap'}, {})
        cr.commit()
        cr.close()

    def test_ir_sequence_date_range_3_unlink(self):
        cr = cursor()
        ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [
            ('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])
        ], {})
        registry('ir.sequence').unlink(cr, ADMIN_USER_ID, ids, {})
        cr.commit()
        cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_3')
        drop_sequence('test_sequence_type_4')


class test_ir_sequence_date_range_generate(unittest2.TestCase):
    """ Create sequence objects and generate some values. """

    def test_ir_sequence_date_range_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_5', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_5', name='Test sequence', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

        cr = cursor()
        f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type_5', {})
        assert all(str(x) == f() for x in xrange(1, 10))
        cr.commit()
        cr.close()

    def test_ir_sequence_date_range_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_6', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_6', name='Test sequence',
                 implementation='no_gap', use_date_range=True)
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

        cr = cursor()
        f = lambda *a: registry('ir.sequence').next_by_code(cr, ADMIN_USER_ID, 'test_sequence_type_6', {})
        assert all(str(x) == f() for x in xrange(1, 10))
        cr.commit()
        cr.close()

    @classmethod
    def tearDownClass(cls):
        drop_sequence('test_sequence_type_5')
        drop_sequence('test_sequence_type_6')


if __name__ == '__main__':
    unittest2.main()
