# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence
# This assume an existing database.
import psycopg2
import unittest2

import openerp
import common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

def registry(model):
    return openerp.modules.registry.RegistryManager.get(DB)[model]

def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

class test_ir_sequence_standard(unittest2.TestCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type', name='Test sequence')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_search(self):
        """ Try a search. """
        cr = cursor()
        ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [], {})
        assert ids
        cr.commit()
        cr.close()

    def test_ir_sequence_draw(self):
        """ Try to draw a number. """
        cr = cursor()
        n = registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type', {})
        assert n
        cr.commit()
        cr.close()

    def test_ir_sequence_draw_twice(self):
        """ Try to draw a number from two transactions. """
        cr0 = cursor()
        cr1 = cursor()
        n0 = registry('ir.sequence').get(cr0, ADMIN_USER_ID, 'test_sequence_type', {})
        assert n0
        n1 = registry('ir.sequence').get(cr1, ADMIN_USER_ID, 'test_sequence_type', {})
        assert n1
        cr0.commit()
        cr1.commit()
        cr0.close()
        cr1.close()

class test_ir_sequence_no_gap(unittest2.TestCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_2', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_2', name='Test sequence',
            implementation='no_gap')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_draw_no_gap(self):
        """ Try to draw a number. """
        cr = cursor()
        n = registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type_2', {})
        assert n
        cr.commit()
        cr.close()

    def test_ir_sequence_draw_twice_no_gap(self):
        """ Try to draw a number from two transactions.
        This is expected to not work.
        """
        cr0 = cursor()
        cr1 = cursor()
        cr1._default_log_exceptions = False # Prevent logging a traceback
        msg_re = '^could not obtain lock on row in relation "ir_sequence"$'
        with self.assertRaisesRegexp(psycopg2.OperationalError, msg_re):
            n0 = registry('ir.sequence').get(cr0, ADMIN_USER_ID, 'test_sequence_type_2', {})
            assert n0
            n1 = registry('ir.sequence').get(cr1, ADMIN_USER_ID, 'test_sequence_type_2', {})
        cr0.close()
        cr1.close()

class test_ir_sequence_change_implementation(unittest2.TestCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_1_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_3', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_3', name='Test sequence')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_4', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_4', name='Test sequence',
            implementation='no_gap')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

    def test_ir_sequence_2_write(self):
        cr = cursor()
        ids = registry('ir.sequence').search(cr, ADMIN_USER_ID,
            [('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])], {})
        registry('ir.sequence').write(cr, ADMIN_USER_ID, ids,
            {'implementation': 'standard'}, {})
        registry('ir.sequence').write(cr, ADMIN_USER_ID, ids,
            {'implementation': 'no_gap'}, {})
        cr.commit()
        cr.close()

    def test_ir_sequence_3_unlink(self):
        cr = cursor()
        ids = registry('ir.sequence').search(cr, ADMIN_USER_ID,
            [('code', 'in', ['test_sequence_type_3', 'test_sequence_type_4'])], {})
        registry('ir.sequence').unlink(cr, ADMIN_USER_ID, ids, {})
        cr.commit()
        cr.close()

class test_ir_sequence_generate(unittest2.TestCase):
    """ Create sequence objects and generate some values. """

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_5', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_5', name='Test sequence')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

        cr = cursor()
        f = lambda *a: registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type_5', {})
        assert all(str(x) == f() for x in xrange(1,1000))
        cr.commit()
        cr.close()

    def test_ir_sequence_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        d = dict(code='test_sequence_type_6', name='Test sequence type')
        c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
        assert c
        d = dict(code='test_sequence_type_6', name='Test sequence')
        c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
        assert c
        cr.commit()
        cr.close()

        cr = cursor()
        f = lambda *a: registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type_6', {})
        assert all(str(x) == f() for x in xrange(1,1000))
        cr.commit()
        cr.close()
        


if __name__ == '__main__':
    unittest2.main()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
