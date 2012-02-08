# -*- coding: utf-8 -*-
import unittest2

import test_orm
import test_ir_sequence
import test_xmlrpc

# This test suite assumes a database.
def make_suite():
    suite = unittest2.TestSuite()
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_ir_sequence))
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_orm))
    return suite

# This test suite creates a database.
def make_suite_no_db():
    suite = unittest2.TestSuite()
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_xmlrpc))
    return suite

# This test suite combines the two above test suites
# (and thus creates a database).
def make_complete_suite():
    suite = unittest2.TestSuite()
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_xmlrpc))
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_ir_sequence))
    suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_orm))
    return suite

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
