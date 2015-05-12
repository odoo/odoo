# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from openerp.tools.translate import quote, unquote, xml_translate

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

    def test_translate_xml_base(self):
        """ Test xml_translate() without formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah blah blah</h1>
                        Put some more text here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah', 'Put some more text here'])

    def test_translate_xml_inline1(self):
        """ Test xml_translate() with formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Put some <b>more text</b> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put some <b>more text</b> here'])

    def test_translate_xml_inline2(self):
        """ Test xml_translate() with formatting elements embedding other elements. """
        terms = []
        source = """<form string="Form stuff">
                        <b><h1>Blah <i>blah</i> blah</h1></b>
                        Put <em>some <b>more text</b></em> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put <em>some <b>more text</b></em> here'])

    def test_translate_xml_inline3(self):
        """ Test xml_translate() with formatting elements without actual text. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <span class="before"/>
                            <h1>Blah blah blah</h1>
                            <span class="after">
                                <i class="hack"/>
                            </span>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah'])

    def test_translate_xml_t(self):
        """ Test xml_translate() with t-* attributes. """
        terms = []
        source = """<t t-name="stuff">
                        stuff before
                        <span t-field="o.name"/>
                        stuff after
                    </t>"""
        result = xml_translate(terms.append, source)
        self.assertEquals(result, source)
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])
