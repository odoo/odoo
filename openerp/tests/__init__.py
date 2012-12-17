# -*- coding: utf-8 -*-
"""
Tests for the OpenERP library.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.
"""

from . import test_acl
from . import test_expression, test_mail, test_ir_sequence, test_orm, \
              test_fields, test_basecase, \
              test_view_validation, test_uninstall, test_misc, test_db_cursor, \
              test_osv, test_translate
from . import test_ir_filters

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
]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
