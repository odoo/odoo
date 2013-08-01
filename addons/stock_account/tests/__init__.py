# -*- coding: utf-8 -*-
"""
Tests for the stock_account module.

This module groups a few sub-modules containing unittest2 test cases.

Tests can be explicitely added to the `fast_suite` or `checks` lists or not.
See the :ref:`test-framework` section in the :ref:`features` list.
"""

import test_standard_prices

fast_suite = [
]

checks = [
    test_standard_prices,
]
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
