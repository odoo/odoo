# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP S.A. http://www.openerp.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import unittest
from openerp.tools.translate import quote, unquote, xml_translator

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

    def test_translate_xml_00(self):
        """ Test xml_translator() without formatting elements. """
        translate = xml_translator()
        terms = []
        callback = lambda t: terms.append(t) or t

        result = translate(callback, """<form string="Form stuff">
                                            <h1>Blah blah blah</h1>
                                            Put some more text here
                                            <field name="foo"/>
                                        </form>""")
        self.assertEquals(result,
            """<form string="Form stuff"><h1>Blah blah blah</h1>Put some more text here<field name="foo"/></form>""")
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah', 'Put some more text here'])

    def test_translate_xml_10(self):
        """ Test xml_translator() with formatting elements. """
        translate = xml_translator()
        terms = []
        callback = lambda t: terms.append(t) or t

        result = translate(callback, """<form string="Form stuff">
                                            <h1>Blah <i>blah</i> blah</h1>
                                            Put some <b>more text</b> here
                                            <field name="foo"/>
                                        </form>""")
        self.assertEquals(result,
            """<form string="Form stuff"><h1>Blah <i>blah</i> blah</h1>Put some <b>more text</b> here<field name="foo"/></form>""")
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put some <b>more text</b> here'])

    def test_translate_xml_20(self):
        """ Test xml_translator() with formatting elements embedding other elements. """
        translate = xml_translator()
        terms = []
        callback = lambda t: terms.append(t) or t

        result = translate(callback, """<form string="Form stuff">
                                            <b><h1>Blah <i>blah</i> blah</h1></b>
                                            Put <em>some <b>more text</b></em> here
                                            <field name="foo"/>
                                        </form>""")
        self.assertEquals(result,
            """<form string="Form stuff"><b><h1>Blah <i>blah</i> blah</h1></b>Put <em>some <b>more text</b></em> here<field name="foo"/></form>""")
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put <em>some <b>more text</b></em> here'])

    def test_translate_xml_30(self):
        """ Test xml_translator() with t-* attributes. """
        translate = xml_translator()
        terms = []
        callback = lambda t: terms.append(t) or t

        result = translate(callback, """<t t-name="stuff">
                                            stuff before
                                            <span t-field="o.name"/>
                                            stuff after
                                        </t>""")
        self.assertEquals(result,
            """<t t-name="stuff">stuff before<span t-field="o.name"/>stuff after</t>""")
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])

    def test_translate_xml_40(self):
        """ Test xml_translator() with <a> elements. """
        translate = xml_translator()
        terms = []
        callback = lambda t: terms.append(t) or t

        source = """<t t-name="stuff">
                        <ul class="nav navbar-nav">
                            <li>
                                <a href="/web#menu_id=42&amp;action=54" class="oe_menu_leaf">
                                    <span class="oe_menu_text">Blah</span>
                                </a>
                            </li>
                            <li id="menu_more_container" class="dropdown" style="display: none;">
                                <a href="#" class="dropdown-toggle" data-toggle="dropdown">More <b class="caret"/></a>
                                <ul id="menu_more" class="dropdown-menu"/>
                            </li>
                        </ul>
                    </t>"""
        result = translate(callback, source)

        self.assertEquals(result,
            """<t t-name="stuff"><ul class="nav navbar-nav"><li><a href="/web#menu_id=42&amp;action=54" class="oe_menu_leaf"><span class="oe_menu_text">Blah</span></a></li><li id="menu_more_container" class="dropdown" style="display: none;"><a href="#" class="dropdown-toggle" data-toggle="dropdown">More <b class="caret"/></a><ul id="menu_more" class="dropdown-menu"/></li></ul></t>""")
        self.assertItemsEqual(terms,
            ['<span class="oe_menu_text">Blah</span>', 'More <b class="caret"/>'])
