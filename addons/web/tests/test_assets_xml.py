# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import re
from unittest.mock import patch
import textwrap
from datetime import datetime
from lxml import etree
import logging

import odoo
from odoo.tests.common import BaseCase, HttpCase, tagged
from odoo.tools import topological_sort
from odoo.addons.base.models.assetsbundle import AssetsBundle, WebAsset


_logger = logging.getLogger(__name__)

class TestStaticInheritanceCommon(odoo.tests.TransactionCase):
    def setUp(self):
        super().setUp()

        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <span>Ho !</span>
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                    <t t-name="template_1_2">
                        <div>And I grew strong</div>
                    </t>
                </templates>
            """,
            '/module_2/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_2_1" t-inherit="module_1.template_1_1" t-inherit-mode="primary">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                        <xpath expr="//span" position="attributes">
                            <attribute name="type">Scary screams</attribute>
                        </xpath>
                        <xpath expr="//div[2]" position="after">
                            <div>But then I spent so many nights thinking how you did me wrong</div>
                        </xpath>
                    </form>
                    <div t-name="template_2_2">
                        <div>And I learned how to get along</div>
                    </div>
                    <form t-inherit="module_1.template_1_2" t-inherit-mode="extension">
                        <xpath expr="//div[1]" position="after">
                            <div>And I learned how to get along</div>
                        </xpath>
                    </form>
                </templates>
            """,
        }
        self._patch = patch.object(WebAsset, '_fetch_content', lambda asset: self.template_files[asset.url])
        self._patch.start()

    def tearDown(self):
        super().tearDown()
        self._patch.stop()

    def renderBundle(self, debug=False):
        files = []
        for url in self.template_files:
            atype = 'text/xml'
            if '.js' in url:
                atype = 'text/javascript'
            files.append({
                'atype': atype,
                'url': url,
                'filename': url,
                'content': None,
                'media': None,
            })
        asset = AssetsBundle('web.test_bundle', files, env=self.env, css=False, js=True)
        # to_node return the files descriptions and generate attachments.
        asset.to_node(css=False, js=False, debug=debug and 'assets' or '')
        content = asset.xml(show_inherit_info=debug)
        return f'<templates xml:space="preserve">\n{content}\n</templates>'

    # Custom Assert
    def assertXMLEqual(self, output, expected):
        self.assertTrue(output)
        self.assertTrue(expected)
        self.assertEqual(etree.fromstring(output), etree.fromstring(expected))

@tagged('assets_bundle', 'static_templates')
class TestStaticInheritance(TestStaticInheritanceCommon):
    # Actual test cases
    def test_static_with_debug_mode(self):
        expected = """
            <templates xml:space="preserve">

                <!-- Filepath: /module_1/static/xml/file_1.xml -->
                <form t-name="template_1_1" random-attr="gloria">
                    <span>Ho !</span>
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>

                <!-- Filepath: /module_1/static/xml/file_1.xml => /module_2/static/xml/file_1.xml -->
                <t t-name="template_1_2">
                    <div>And I grew strong</div>
                        <!-- Filepath: /module_2/static/xml/file_1.xml ; position="after" ; {'expr': '//div[1]'} --><div>And I learned how to get along</div>
                </t>

                <!-- Filepath: /module_1/static/xml/file_1.xml => /module_2/static/xml/file_1.xml -->
                <form t-name="template_2_1" random-attr="gloria"><!-- Filepath: /module_2/static/xml/file_1.xml ; position="attributes" ; {'expr': '//span'} -->
                    <span type="Scary screams">Ho !</span>
                    <div>At first I was afraid</div>
                        <!-- Filepath: /module_2/static/xml/file_1.xml ; position="after" ; {'expr': '//div[1]'} --><div>I was petrified</div>
                        <!-- Filepath: /module_2/static/xml/file_1.xml ; position="after" ; {'expr': '//div[2]'} --><div>But then I spent so many nights thinking how you did me wrong</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>

                <!-- Filepath: /module_2/static/xml/file_1.xml -->
                <div t-name="template_2_2">
                    <div>And I learned how to get along</div>
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=True), expected)

    def test_static_inheritance_01(self):
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1" random-attr="gloria">
                    <span>Ho !</span>
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <t t-name="template_1_2">
                    <div>And I grew strong</div>
                    <div>And I learned how to get along</div>
                </t>
                <form t-name="template_2_1" random-attr="gloria">
                    <span type="Scary screams">Ho !</span>
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>But then I spent so many nights thinking how you did me wrong</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <div t-name="template_2_2">
                    <div>And I learned how to get along</div>
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_inheritance_02(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                    <form t-name="template_1_2" t-inherit="template_1_1" added="true">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                    </form>
                </templates>
            """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1" random-attr="gloria">
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_2" random-attr="gloria" added="true">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_inheritance_03(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1">
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                    <form t-name="template_1_2" t-inherit="template_1_1" added="true">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                    </form>
                    <form t-name="template_1_3" t-inherit="template_1_2" added="false" other="here">
                        <xpath expr="//div[2]" position="replace"/>
                    </form>
                </templates>
            '''
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1">
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_2" added="true">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_3" added="false" other="here">
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_inheritance_in_same_module(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1">
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                </templates>
            ''',

            '/module_1/static/xml/file_2.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="primary">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                    </form>
                </templates>
            '''
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1">
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_2">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_inheritance_in_same_file(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1">
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                    <form t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="primary">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                    </form>
                </templates>
            ''',
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1">
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_2">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_inherit_extended_template(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1">
                        <div>At first I was afraid</div>
                        <div>Kept thinking I could never live without you by my side</div>
                    </form>
                    <form t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="//div[1]" position="after">
                            <div>I was petrified</div>
                        </xpath>
                    </form>
                    <form t-name="template_1_3" t-inherit="template_1_1" t-inherit-mode="primary">
                        <xpath expr="//div[3]" position="after">
                            <div>But then I spent so many nights thinking how you did me wrong</div>
                        </xpath>
                    </form>
                </templates>
            ''',
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <form t-name="template_1_3">
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>Kept thinking I could never live without you by my side</div>
                    <div>But then I spent so many nights thinking how you did me wrong</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_sibling_extension(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1">
                        <div>I am a man of constant sorrow</div>
                        <div>I've seen trouble all my days</div>
                    </form>
                </templates>
            ''',

            '/module_2/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_2_1" t-inherit="module_1.template_1_1" t-inherit-mode="extension">
                        <xpath expr="//div[1]" position="after">
                            <div>In constant sorrow all through his days</div>
                        </xpath>
                    </form>
                </templates>
            ''',

            '/module_3/static/xml/file_1.xml': '''
                <templates id="template" xml:space="preserve">
                    <form t-name="template_3_1" t-inherit="module_1.template_1_1" t-inherit-mode="extension">
                        <xpath expr="//div[2]" position="after">
                            <div>Oh Brother !</div>
                        </xpath>
                    </form>
                </templates>
            '''
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1">
                    <div>I am a man of constant sorrow</div>
                    <div>In constant sorrow all through his days</div>
                    <div>Oh Brother !</div>
                    <div>I've seen trouble all my days</div>
                </form>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_static_misordered_modules(self):
        files = self.template_files
        self.template_files = {
            '/module_2/static/xml/file_1.xml': files['/module_2/static/xml/file_1.xml'],
            '/module_1/static/xml/file_1.xml': files['/module_1/static/xml/file_1.xml'],
        }
        with self.assertRaises(ValueError) as ve:
            self.renderBundle(debug=False)

        self.assertEqual(
            str(ve.exception),
            "Module 'module_1' not loaded or inexistent (try to inherit 'template_1_1'), or templates of addon being loaded 'module_2' are misordered (template 'template_2_1')"
        )

    def test_static_misordered_templates(self):
        self.template_files['/module_2/static/xml/file_1.xml'] = """
            <templates id="template" xml:space="preserve">
                <form t-name="template_2_1" t-inherit="module_2.template_2_2" t-inherit-mode="primary">
                    <xpath expr="//div[1]" position="after">
                        <div>I was petrified</div>
                    </xpath>
                </form>
                <div t-name="template_2_2">
                    <div>And I learned how to get along</div>
                </div>
            </templates>
        """
        with self.assertRaises(ValueError) as ve:
            self.renderBundle(debug=False)

        self.assertEqual(
            str(ve.exception),
            "Cannot create 'module_2.template_2_1' because the template to inherit 'module_2.template_2_2' is not found.",
        )

    def test_replace_in_debug_mode(self):
        """
        Replacing a template's meta definition in place doesn't keep the original attrs of the template
        """
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">And I grew strong</div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <div overriden-attr="overriden" t-name="template_1_1">
                    And I grew strong
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_replace_in_debug_mode2(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="." position="replace">
                            <div>
                                And I grew strong
                                <p>And I learned how to get along</p>
                                And so you're back
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <div t-name="template_1_1">
                    And I grew strong
                    <p>And I learned how to get along</p>
                    And so you're back
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_replace_in_debug_mode3(self):
        """Text outside of a div which will replace a whole template
        becomes outside of the template
        This doesn't mean anything in terms of the business of template inheritance
        But it is in the XPATH specs"""
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="." position="replace">
                            <div>
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                            And so you're back
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <div t-name="template_1_1">
                    And I grew strong
                    <p>And I learned how to get along</p>
                </div>
                And so you're back
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_replace_root_node_tag(self):
        """
        Root node IS targeted by //NODE_TAG in xpath
        """
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                        <form>Inner Form</form>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="//form" position="replace">
                            <div>
                                Form replacer
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <div t-name="template_1_1">
                    Form replacer
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_replace_root_node_tag_in_primary(self):
        """
        Root node IS targeted by //NODE_TAG in xpath
        """
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                        <form>Inner Form</form>
                    </form>
                    <form t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="primary">
                        <xpath expr="//form" position="replace">
                            <div>Form replacer</div>
                        </xpath>
                    </form>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1" random-attr="gloria">
                    <div>At first I was afraid</div>
                    <form>Inner Form</form>
                </form>
                <div t-name="template_1_2">
                    Form replacer
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_primary_replace_debug(self):
        """
        The inheriting template has got both its own defining attrs
        and new ones if one is to replace its defining root node
        """
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_1_2">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_replace_in_nodebug_mode1(self):
        """Comments already in the arch are ignored"""
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="." position="replace">
                            <div>
                                <!-- Random Comment -->
                                And I grew strong
                                <p>And I learned how to get along</p>
                                And so you're back
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <div t-name="template_1_1">
                    And I grew strong
                    <p>And I learned how to get along</p>
                    And so you're back
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_from_dotted_tname_1(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="module_1.template_1_1.dot" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1.dot" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="module_1.template_1_1.dot" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_1_2">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_from_dotted_tname_2(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1.dot" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="template_1_1.dot" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1.dot" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_1_2">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_from_dotted_tname_2bis(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="template_1_1.dot" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="module_1.template_1_1.dot" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1.dot" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_1_2">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_from_dotted_tname_2ter(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="module_1" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                    <t t-name="template_1_2" t-inherit="module_1" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
                """,
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="module_1" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_1_2">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_from_dotted_tname_3(self):
        self.template_files = {
            '/module_1/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <form t-name="module_1.template_1_1.dot" random-attr="gloria">
                        <div>At first I was afraid</div>
                    </form>
                </templates>
                """,

            '/module_2/static/xml/file_1.xml': """
                <templates id="template" xml:space="preserve">
                    <t t-name="template_2_1" t-inherit="module_1.template_1_1.dot" t-inherit-mode="primary">
                        <xpath expr="." position="replace">
                            <div overriden-attr="overriden">
                                And I grew strong
                                <p>And I learned how to get along</p>
                            </div>
                        </xpath>
                    </t>
                </templates>
            """
        }
        expected = """
            <templates xml:space="preserve">
                <form t-name="module_1.template_1_1.dot" random-attr="gloria">
                    <div>At first I was afraid</div>
                 </form>
                 <div overriden-attr="overriden" t-name="template_2_1">
                    And I grew strong
                    <p>And I learned how to get along</p>
                 </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)

    def test_inherit_and_qweb_extend(self):
        self.template_files['/module_1/static/xml/file_2.xml'] = """
                <templates id="template" xml:space="preserve">
                    <t t-name="template_qw_1">
                        <div>111</div>
                    </t>
                    <form t-inherit="template_1_1" t-inherit-mode="extension">
                        <xpath expr="//span[1]" position="replace">
                            <article>!!!</article>
                        </xpath>
                    </form>
                    <t t-name="template_qw_2">
                        <div>222</div>
                    </t>
                    <t t-extend="template_qw_1">
                        <t t-jquery="div" t-operation="after">
                            <div>333</div>
                        </t>
                    </t>
                </templates>
            """

        expected = """
            <templates xml:space="preserve">
                <form t-name="template_1_1" random-attr="gloria">
                    <article>!!!</article>
                    <div>At first I was afraid</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <t t-name="template_1_2">
                    <div>And I grew strong</div>
                    <div>And I learned how to get along</div>
                </t>
                <t t-name="template_qw_1">
                    <div>111</div>
                </t>
                <t t-name="template_qw_2">
                    <div>222</div>
                </t>
                <t t-extend="template_qw_1">
                    <t t-jquery="div" t-operation="after">
                        <div>333</div>
                    </t>
                </t>
                <form t-name="template_2_1" random-attr="gloria">
                    <span type="Scary screams">Ho !</span>
                    <div>At first I was afraid</div>
                    <div>I was petrified</div>
                    <div>But then I spent so many nights thinking how you did me wrong</div>
                    <div>Kept thinking I could never live without you by my side</div>
                </form>
                <div t-name="template_2_2">
                    <div>And I learned how to get along</div>
                </div>
            </templates>
        """
        self.assertXMLEqual(self.renderBundle(debug=False), expected)


@tagged('-standard', 'assets_bundle', 'static_templates_performance')
class TestStaticInheritancePerformance(TestStaticInheritanceCommon):
    def _sick_script(self, nMod, nFilePerMod, nTemplatePerFile, stepInheritInModule=2, stepInheritPreviousModule=3):
        """
        Make a sick amount of templates to test perf
        nMod modules
        each module: has nFilesPerModule files, each of which contains nTemplatePerFile templates
        """
        self.asset_paths = []
        self.template_files = {}
        number_templates = 0
        for m in range(nMod):
            for f in range(nFilePerMod):
                mname = 'mod_%s' % m
                fname = 'mod_%s/folder/file_%s.xml' % (m, f)
                self.asset_paths.append((fname, mname, 'bundle_1'))

                _file = '<templates id="template" xml:space="preserve">'

                for t in range(nTemplatePerFile):
                    _template = ''
                    if t % stepInheritInModule or t % stepInheritPreviousModule or t == 0:
                        _template += """
                            <div t-name="template_%(t_number)s_mod_%(m_number)s">
                                <div>Parent</div>
                            </div>
                        """

                    elif not t % stepInheritInModule and t >= 1:
                        _template += """
                            <div t-name="template_%(t_number)s_mod_%(m_number)s"
                                t-inherit="template_%(t_inherit)s_mod_%(m_number)s"
                                t-inherit-mode="primary">
                                <xpath expr="/div/div[1]" position="before">
                                    <div>Sick XPath</div>
                                </xpath>
                            </div>
                        """

                    elif not t % stepInheritPreviousModule and m >= 1:
                        _template += """
                            <div t-name="template_%(t_number)s_mod_%(m_number)s"
                                t-inherit="mod_%(m_module_inherit)s.template_%(t_module_inherit)s_mod_%(m_module_inherit)s"
                                t-inherit-mode="primary">
                                <xpath expr="/div/div[1]" position="inside">
                                    <div>Mental XPath</div>
                                </xpath>
                            </div>
                        """
                    if _template:
                        number_templates += 1

                    _template_number = 1000 * f + t
                    _file += _template % {
                        't_number': _template_number,
                        'm_number': m,
                        't_inherit': _template_number - 1,
                        't_module_inherit': _template_number,
                        'm_module_inherit': m - 1,
                    }
                _file += '</templates>'

                self.template_files[fname] = _file
        self.assertEqual(number_templates, nMod * nFilePerMod * nTemplatePerFile)

    def test_static_templates_treatment_linearity(self):
        # With 2500 templates for starters
        nMod, nFilePerMod, nTemplatePerFile = 50, 5, 10
        self._sick_script(nMod, nFilePerMod, nTemplatePerFile)

        before = datetime.now()
        contents = self.renderBundle(debug=False)
        after = datetime.now()
        delta2500 = after - before
        _logger.runbot('Static Templates Inheritance: 2500 templates treated in %s seconds' % delta2500.total_seconds())

        whole_tree = etree.fromstring(contents)
        self.assertEqual(len(whole_tree), nMod * nFilePerMod * nTemplatePerFile)

        # With 25000 templates next
        nMod, nFilePerMod, nTemplatePerFile = 50, 5, 100
        self._sick_script(nMod, nFilePerMod, nTemplatePerFile)

        before = datetime.now()
        self.renderBundle(debug=False)
        after = datetime.now()
        delta25000 = after - before

        time_ratio = delta25000.total_seconds() / delta2500.total_seconds()
        _logger.runbot('Static Templates Inheritance: 25000 templates treated in %s seconds' % delta25000.total_seconds())
        _logger.runbot('Static Templates Inheritance: Computed linearity ratio: %s' % time_ratio)
        self.assertLessEqual(time_ratio, 14)
