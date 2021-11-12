# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import TestCase


class TestTestSuite(TestCase):
    test_tags = {'standard', 'at_install'}
    test_module = 'base'

    def test_test_suite(self):
        """ Check that OdooSuite handles unittest.TestCase correctly. """
