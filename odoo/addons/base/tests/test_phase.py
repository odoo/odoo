# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import common


#: Stores state information across multiple test classes
test_state = None

def setUpModule():
    global test_state
    test_state = {}

def tearDownModule():
    global test_state
    test_state = None


class TestPhaseInstall00(unittest.TestCase):
    """
    WARNING: Relies on tests being run in alphabetical order
    """
    @classmethod
    def setUpClass(cls):
        cls.state = None

    def test_00_setup(self):
        type(self).state = 'init'

    @common.at_install(False)
    def test_01_no_install(self):
        type(self).state = 'error'

    def test_02_check(self):
        self.assertEqual(self.state, 'init',
                         "Testcase state should not have been transitioned from 00")


class TestPhaseInstall01(unittest.TestCase):
    at_install = False

    def test_default_norun(self):
        self.fail("An unmarket test in a non-at-install case should not run")

    @common.at_install(True)
    def test_set_run(self):
        test_state['set_at_install'] = True


class TestPhaseInstall02(unittest.TestCase):
    """
    Can't put the check for test_set_run in the same class: if
    @common.at_install does not work for test_set_run, it won't work for
    the other one either. Thus move checking of whether test_set_run has
    correctly run indeed to a separate class.

    Warning: relies on *classes* being run in alphabetical order in test
    modules
    """
    def test_check_state(self):
        self.assertTrue(test_state.get('set_at_install'),
                        "The flag should be set if local overriding of runstate")
