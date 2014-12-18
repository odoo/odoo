# -*- coding: utf-8 -*-
from openerp.tests import common

class TestBasicInheritance(common.TransactionCase):
    def test_inherit_method(self):
        env = self.env

        a = env['inheritance.0'].create({'name': 'A'})
        b = env['inheritance.1'].create({'name': 'B'})

        self.assertEqual(
        a.call()
            ,
        """
        This is model 0 record A
        """.strip()
        )
        self.assertEqual(
        b.call()
            ,
        """
        This is model 1 record B
        """.strip()
        )
