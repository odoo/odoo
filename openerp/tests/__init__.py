# -*- coding: utf-8 -*-
"""
Tests for the OpenERP library.

This module groups a few sub-modules containing unittest2 test cases.

Some of those test sub-modules are explicitely listed in the `fast_suite`
variable.  Most of the tests should be considered fast enough to be included in
that `fast_suite` list and only tests that take a long time to run (e.g. more
than a minute) should not be listed.

Some other test sub-modules are sanity checks explicitely listed in the
`checks` variable. These test sub-modules are invariants that must be
full-filled at any time. They are expected to always pass: obviously they must
pass right after the module is installed, but they must also pass after any
other module is installed, after a migration, or even after the database was
put in production for a few months.
"""

import test_orm
import test_ir_sequence
import test_xmlrpc

fast_suite = [
    test_xmlrpc, # Creates a database
    test_ir_sequence, # Assume an existing database
    ]

checks = [
    test_orm, # Assume an existing database
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
