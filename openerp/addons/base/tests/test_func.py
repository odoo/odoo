# -*- coding: utf-8 -*-
import functools
import unittest2

from openerp.tools.func import compose

class TestCompose(unittest2.TestCase):
    def test_basic(self):
        str_add = compose(str, lambda a, b: a + b)
        self.assertEqual(
            str_add(1, 2),
            "3")

    def test_decorator(self):
        """ ensure compose() can be partially applied as a decorator
        """
        @functools.partial(compose, unicode)
        def mul(a, b):
            return a * b

        self.assertEqual(mul(5, 42), u"210")

