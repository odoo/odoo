# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from openerp.tools.translate import quote, unquote

class TranslationToolsTestCase(unittest.TestCase):

    def test_quote_unquote(self):

        def test_string(str):
            quoted = quote(str)
            #print "\n1:", repr(str)
            #print "2:", repr(quoted)
            unquoted = unquote("".join(quoted.split('"\n"')))
            #print "3:", repr(unquoted)
            self.assertEquals(str, unquoted)

        test_string("""test \nall kinds\n \n o\r
         \\\\ nope\n\n"
         """)

        # The ones with 1+ backslashes directly followed by
        # a newline or literal N can fail... we would need a
        # state-machine parser to handle these, but this would
        # be much slower so it's better to avoid them at the moment
        self.assertRaises(AssertionError, quote, """test \nall kinds\n\no\r
         \\\\nope\n\n"
         """)
