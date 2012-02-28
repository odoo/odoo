# -*- coding: utf-8 -*-
"""
Tests for the OpenERP library.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.
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
