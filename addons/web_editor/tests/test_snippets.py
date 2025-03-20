# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.tests import TransactionCase


class TestViews(TransactionCase):

    def _assertXmlEqual(self, result, expectation):
        parser = etree.XMLParser(remove_blank_text=True)
        result = etree.tostring(
            etree.fromstring(result, parser=parser)
        )
        expectation = etree.tostring(
            etree.fromstring(expectation, parser=parser)
        )
        self.assertEqual(result, expectation)

    def test_data_snippet_inheritance(self):
        View = self.env['ir.ui.view']
        snippets = View.create({
            'name': 'TestSnippets',
            'type': 'qweb',
            'arch': '''<snippets id="snippet_test_structure" string="Test Panel">
                           <t t-snippet="web_editor.test_snippet"/>
                           <t t-snippet="web_editor.test_snippet_call"/>
                       </snippets>
                    ''',
            'key': 'web_editor.test_snippets',
        })
        snippet = View.create({
            'name': 'TestSnippet',
            'type': 'qweb',
            'arch': '''<div id="a">
                           <div id="b">hello</div>
                           <div id="c"><t t-call="web_editor.test_t_call"/></div>
                           <div id="d"><t t-out="0"/></div>
                       </div>
                    ''',
            'key': 'web_editor.test_snippet',
        })
        View.create({
            'name': 'TestTCall',
            'type': 'qweb',
            'arch': '<div id="e">world</div>',
            'key': 'web_editor.test_t_call',
        })
        t_snippet_call = View.create({
            'name': 'TestTSnippetCall',
            'type': 'qweb',
            'arch': '''<div id="f">
                           <div id="g">!</div>
                           <div id="h">
                               <t t-snippet-call="web_editor.test_snippet"><div id="i">to everyone</div></t>
                           </div>
                       </div>
                    ''',
            'key': 'web_editor.test_snippet_call',
        })

        self._assertXmlEqual(
            self.env['ir.qweb']._render('web_editor.test_snippets'),
            f'''
            <snippets id="snippet_test_structure" string="Test Panel">
                <div name="TestSnippet" data-oe-type="snippet" data-o-image-preview="" data-oe-thumbnail="oe-thumbnail" data-oe-snippet-id="{snippet.id}" data-oe-keywords="">
                     <div id="a" data-snippet="test_snippet"><div id="b">hello</div><div id="c"><div id="e">world</div></div><div id="d"/></div>
                </div>
                <div name="TestTSnippetCall" data-oe-type="snippet" data-o-image-preview="" data-oe-thumbnail="oe-thumbnail" data-oe-snippet-id="{t_snippet_call.id}" data-oe-keywords="">
                    <div id="f" data-snippet="test_snippet_call">
                        <div id="g">!</div>
                        <div id="h">
                            <div id="a" data-snippet="test_snippet"><div id="b">hello</div><div id="c"><div id="e">world</div></div><div id="d"><div id="i">to everyone</div></div></div>
                        </div>
                    </div>
                </div>
            </snippets>
            '''
        )
