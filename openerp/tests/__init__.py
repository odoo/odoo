# -*- coding: utf-8 -*-
"""
Tests for the OpenERP library.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.
"""
import test_acl
import test_basecase
import test_db_cursor
import test_expression
import test_fields
import test_ir_filters
import test_ir_sequence
import test_mail
import test_misc
import test_orm
import test_osv
import test_translate
import test_view_validation
import test_qweb
import test_func
# This need a change in `oe run-tests` to only run fast_suite + checks by default.
# import test_xmlrpc

fast_suite = [
    test_ir_sequence,
    test_ir_filters
]

checks = [
    test_acl,
    test_expression,
    test_mail,
    test_db_cursor,
    test_orm,
    test_fields,
    test_basecase,
    test_view_validation,
    test_misc,
    test_osv,
    test_translate,
    test_qweb,
    test_func,
]
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
