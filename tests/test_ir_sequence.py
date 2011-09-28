# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence
import os
import psycopg2
import time
import unittest2
import xmlrpclib

import openerp
import common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

setUpModule = common.setUpModule
tearDownModule = common.tearDownModule

def registry(model):
    return openerp.modules.registry.RegistryManager.get(DB)[model]

def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

class test_ir_sequence_standard(unittest2.TestCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_type', name='Test sequence type')
            c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
            assert c
            d = dict(code='test_sequence_type', name='Test sequence')
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_search(self):
        """ Try a search. """
        cr = cursor()
        try:
            ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [], {})
            assert ids
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_draw(self):
        """ Try to draw a number. """
        cr = cursor()
        try:
            n = registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type', {})
            assert n
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_draw_twice(self):
        """ Try to draw a number from two transactions. """
        cr0 = cursor()
        cr1 = cursor()
        try:
            n0 = registry('ir.sequence').get(cr0, ADMIN_USER_ID, 'test_sequence_type', {})
            assert n0
            n1 = registry('ir.sequence').get(cr1, ADMIN_USER_ID, 'test_sequence_type', {})
            assert n1
            cr0.commit()
            cr1.commit()
        finally:
            cr0.close()
            cr1.close()

class test_ir_sequence_no_gap(unittest2.TestCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_create_no_gap(self):
        """ Try to create a sequence object. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_type_2', name='Test sequence type')
            c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
            assert c
            d = dict(code='test_sequence_type_2', name='Test sequence',
                implementation='no_gap')
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_draw_no_gap(self):
        """ Try to draw a number. """
        cr = cursor()
        try:
            n = registry('ir.sequence').get(cr, ADMIN_USER_ID, 'test_sequence_type_2', {})
            assert n
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_draw_twice_no_gap(self):
        """ Try to draw a number from two transactions.
        This is expected to not work.
        """
        cr0 = cursor()
        cr1 = cursor()
        try:
            msg_re = '^could not obtain lock on row in relation "ir_sequence"$'
            with self.assertRaisesRegexp(psycopg2.OperationalError, msg_re):
                n0 = registry('ir.sequence').get(cr0, ADMIN_USER_ID, 'test_sequence_type_2', {})
                assert n0
                n1 = registry('ir.sequence').get(cr1, ADMIN_USER_ID, 'test_sequence_type_2', {})
        finally:
            cr0.close()
            cr1.close()


if __name__ == '__main__':
    unittest2.main()

