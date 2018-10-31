# -*- coding: utf-8 -*-
"""
Test basic features of test cases
"""
from odoo.tests.common import TransactionCase, users

UNIQUE_NAME = "I'm very special"

class TestTestCases(TransactionCase):

    @users('__system__', 'admin')
    def test_cleanup(self):
        """Tests that cleanups between @users runs were properly executed"""
        self.env['test_testing_utilities.c'].create({'name': UNIQUE_NAME})
        uniques = self.env['test_testing_utilities.c'].search([('name', '=', UNIQUE_NAME)])
        self.assertEqual(len(uniques), 1, "Too many uniques - missing cleanup!")
