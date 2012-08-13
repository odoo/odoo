# -*- coding: utf-8 -*-
"""
Tests for the OpenERP library.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.
"""

from . import test_expression, test_ir_sequence, test_orm,\
              test_uninstall

fast_suite = [
    test_ir_sequence,
]

checks = [
    test_expression,
    test_orm,
]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
