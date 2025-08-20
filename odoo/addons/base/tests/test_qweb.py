# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import markupsafe

from lxml import etree, html
from lxml.builder import E
from textwrap import dedent

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.models.ir_qweb import QWebError, render
from odoo.tools import file_open, misc, mute_logger
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.exceptions import UserError, MissingError

unsafe_eval = eval


@tagged('post_install', '-at_install')
class TestQWebTField(TransactionCase):
    def setUp(self):
        super(TestQWebTField, self).setUp()
        self.env_branding = self.env(context={'inherit_branding': True})
        self.engine = self.env_branding['ir.qweb']

    def test_trivial(self):
        field = etree.Element('span', {'t-field': 'company.name'})
        company = self.env['res.company'].create({'name': "My Test Company"})

        result = self.engine._render(field, {'company': company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring('<span data-oe-model="res.company" data-oe-id="%d" '
                  'data-oe-field="name" data-oe-type="char" '
                  'data-oe-expression="company.name">%s</span>' % (
                company.id,
                "My Test Company",
            )),
        )

    def test_i18n(self):
        field = etree.Element('span', {'t-field': 'company.name'})
        s = "Testing «ταБЬℓσ»: 1<2 & 4+1>3, now 20% off!"
        company = self.env['res.company'].create({'name': s})

        result = self.engine._render(field, {'company': company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring('<span data-oe-model="res.company" data-oe-id="%d" '
                  'data-oe-field="name" data-oe-type="char" '
                  'data-oe-expression="company.name">%s</span>' % (
                company.id,
                misc.html_escape(s),
            )),
        )

    def test_reject_crummy_tags(self):
        field = etree.Element('td', {'t-field': 'company.name'})

        with self.assertRaisesRegex(QWebError, r'QWeb widgets do not work correctly'):
            self.engine._render(field, {'company': None})

    def test_reject_t_tag(self):
        field = etree.Element('t', {'t-field': 'company.name'})

        with self.assertRaisesRegex(QWebError, r't-field can not be used on a t element'):
            self.engine._render(field, {'company': None})

    def test_render_t_options(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy"><root><span t-esc="5" t-options="{'widget': 'char'}" t-options-widget="'float'" t-options-precision="4"/></root></t>
            """
        })
        text = etree.fromstring(self.env['ir.qweb']._render(view1.id)).find('span').text
        self.assertEqual(text, '5.0000')

    def test_xss_breakout(self):
        view = self.env['ir.ui.view'].create({
            'name': 'dummy', 'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <root>
                        <script type="application/javascript">
                            var s = <t t-esc="json.dumps({'key': malicious})"/>;
                        </script>
                    </root>
                </t>
            """
        })
        rendered = self.env['ir.qweb']._render(view.id, {'malicious': '1</script><script>alert("pwned")</script><script>'})
        self.assertIn('alert', rendered, "%r doesn't seem to be rendered" % rendered)
        doc = etree.fromstring(rendered)
        self.assertEqual(len(doc.xpath('//script')), 1)

    def test_default_value(self):
        Partner = self.env['res.partner']
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="out-field-default">
                <div t-field="record.name">
                    DEFAULT
                    <t t-out="'Text'" />
                </div>
            </t>''',
        })

        # record.name is non-empty
        result = """
                <div>My Company</div>
        """
        rendered = self.env['ir.qweb']._render(t.id, {
            'record': Partner.new({'name': 'My Company'})
        })
        self.assertEqual(str(rendered.strip()), result.strip(), "")

        # record.name is empty but not False or None, we should render depending on force_display
        result = """
                <div></div>
        """
        rendered = self.env['ir.qweb']._render(t.id, {
            'record': Partner.new({'name': ''})
        })
        self.assertEqual(str(rendered.strip()), result.strip())

        # record.name is False or None, we should render field default value
        result = """
                <div>
                    DEFAULT
                    Text
                </div>
        """
        rendered = self.env['ir.qweb']._render(t.id, {
            'record': Partner.new({})
        })
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_no_value_no_default_value(self):
        # no value, no default value with attributes on t-field
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="out-field-default">
                <div t-field="record.name"/>
            </t>''',
        })
        result = """
                <div data-oe-xpath="/t[1]/div[1]" data-oe-model="res.partner" data-oe-field="name" data-oe-type="char" data-oe-expression="record.name"></div>
        """
        # inherit_branding puts attribute on the field tag as well as force the display in case the field is empty
        rendered = self.env['ir.qweb'].with_context(inherit_branding=True)._render(t.id, {
            'record': self.env['res.partner'].new({}),
        })
        self.assertEqual(str(rendered.strip()), result.strip())


@tagged('post_install', '-at_install')
class TestQWebNS(TransactionCase):
    def test_render_static_xml_with_namespace(self):
        """ Test the rendering on a namespaced view with no static content. The resulting string should be untouched.
        """
        expected_result = """
            <root>
                <h:table xmlns:h="http://www.example.org/table">
                    <h:tr>
                        <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
                <f:table xmlns:f="http://www.example.org/furniture">
                    <f:width>80</f:width>
                </f:table>
            </root>
        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), etree.fromstring(expected_result))

    def test_render_static_xml_with_namespace_2(self):
        """ Test the rendering on a namespaced view with no static content. The resulting string should be untouched.
        """
        expected_result = """
            <html xmlns="http://www.w3.org/HTML/1998/html4" xmlns:xdc="http://www.xml.com/books">
                <head>
                    <title>Book Review</title>
                </head>
                <body>
                    <xdc:bookreview>
                        <xdc:title>XML: A Primer</xdc:title>
                        <table>
                            <tr align="center">
                                <td>Author</td><td>Price</td>
                                <td>Pages</td><td>Date</td>
                            </tr>
                            <tr align="left">
                                <td><xdc:author>Simon St. Laurent</xdc:author></td>
                                <td><xdc:price>31.98</xdc:price></td>
                                <td><xdc:pages>352</xdc:pages></td>
                                <td><xdc:date>1998/01</xdc:date></td>
                            </tr>
                        </table>
                    </xdc:bookreview>
                </body>
            </html>
        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), etree.fromstring(expected_result))

    def test_render_static_xml_with_useless_distributed_namespace(self):
        """ Test that redundant namespaces are stripped upon rendering.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <root>
                        <h:table xmlns:h="http://www.example.org/table">
                            <h:tr xmlns:h="http://www.example.org/table">
                                <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                                <h:td xmlns:h="http://www.example.org/table">Bananas</h:td>
                            </h:tr>
                        </h:table>
                    </root>
                </t>
            """
        })

        expected_result = etree.fromstring("""
            <root>
                <h:table xmlns:h="http://www.example.org/table">
                    <h:tr>
                        <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
            </root>
        """)

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_static_xml_with_namespace_3(self):
        expected_result = """
            <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd"></cfdi:Comprobante>
        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), etree.fromstring(expected_result))

    def test_render_static_xml_with_namespace_dynamic(self):
        """ Test the rendering on a namespaced view with dynamic URI (need default namespace uri).
        """
        tempate = """
            <root xmlns:h="https://default.namespace.url/h">
                <h:table t-att="{'xmlns:h': h1}">
                    <h:tr>
                        <h:td t-att="{'xmlns:h': h2}">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
            </root>
        """
        expected_result = """
            <root xmlns:h="https://default.namespace.url/h">
                <h:table xmlns:h="%(h1)s">
                    <h:tr>
                        <h:td xmlns:h="%(h2)s">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
            </root>
        """

        values = dict(h1="http://www.example.org/table", h2="http://www.w3.org/TD/html4/")

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % tempate
        })

        rendering = self.env['ir.qweb']._render(view1.id, values)

        self.assertEqual(etree.fromstring(rendering), etree.fromstring(expected_result % values))

    def test_render_static_xml_with_namespace_dynamic_2(self):
        """ Test the rendering on a namespaced view with dynamic URI (need default namespace uri).
        Default URIs must be differents.
        """
        tempate = """
            <root xmlns:f="https://default.namespace.url/f" xmlns:h="https://default.namespace.url/h" >
                <h:table t-att="{'xmlns:h': h1}">
                    <h:tr>
                        <h:td t-att="{'xmlns:h': h2}">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
                <f:table t-att="{'xmlns:f': f}">
                    <f:width>80</f:width>
                </f:table>
            </root>
        """
        expected_result = """
            <root xmlns:f="https://default.namespace.url/f" xmlns:h="https://default.namespace.url/h">
                <h:table xmlns:h="%(h1)s">
                    <h:tr>
                        <h:td xmlns:h="%(h2)s">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
                <f:table xmlns:f="%(f)s">
                    <f:width>80</f:width>
                </f:table>
            </root>
        """

        values = dict(h1="http://www.example.org/table", h2="http://www.w3.org/TD/html4/", f="http://www.example.org/furniture")

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % tempate
        })

        rendering = self.env['ir.qweb']._render(view1.id, values)

        self.assertEqual(etree.fromstring(rendering), etree.fromstring(expected_result % values))

    def test_render_dynamic_xml_with_namespace_t_esc(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-esc attribute correctly
        handles the t-esc attribute and keep the ns declaration.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-esc="'test'"/>
                </t>
            """
        })

        expected_result = etree.fromstring("""<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">test</Invoice>""")

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_dynamic_xml_with_namespace_t_esc_with_useless_distributed_namespace(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-esc attribute correctly
        handles the t-esc attribute and keep the ns declaration, and distribute correctly the ns declaration to its children.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-attf-test="test">
                        <cac:Test xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">blabla</cac:Test>
                    </Invoice>
                </t>
            """
        })

        expected_result = etree.fromstring("""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" test="test">
                <cac:Test>blabla</cac:Test>
            </Invoice>
        """)

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_dynamic_xml_with_namespace_t_attf(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-attf attribute correctly
        handles the t-attf attribute and keep the ns declaration.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <root>
                        <h:table xmlns:h="http://www.example.org/table">
                            <h:tr>
                                <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                                <h:td>Bananas</h:td>
                            </h:tr>
                        </h:table>
                        <f:table xmlns:f="http://www.example.org/furniture">
                            <f:width t-attf-test="1">80</f:width>
                        </f:table>
                    </root>
                </t>
            """
        })

        expected_result = etree.fromstring("""
            <root>
                <h:table xmlns:h="http://www.example.org/table">
                    <h:tr>
                        <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
                <f:table xmlns:f="http://www.example.org/furniture">
                    <f:width test="1">80</f:width>
                </f:table>
            </root>
        """)

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_dynamic_xml_with_namespace_t_attf_with_useless_distributed_namespace(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-attf attribute correctly
        handles the t-attf attribute and that redundant namespaces are stripped upon rendering.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                <root>
                    <h:table xmlns:h="http://www.example.org/table">
                        <h:tr>
                            <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                            <h:td>Bananas</h:td>
                        </h:tr>
                    </h:table>
                    <f:table xmlns:f="http://www.example.org/furniture">
                        <f:width xmlns:f="http://www.example.org/furniture" t-attf-test="1">80</f:width>
                    </f:table>
                </root>

                </t>
            """
        })

        expected_result = etree.fromstring("""
                <root>
                    <h:table xmlns:h="http://www.example.org/table">
                        <h:tr>
                            <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                            <h:td>Bananas</h:td>
                        </h:tr>
                    </h:table>
                    <f:table xmlns:f="http://www.example.org/furniture">
                        <f:width test="1">80</f:width>
                    </f:table>
                </root>

        """)

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_dynamic_xml_with_namespace_2(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                        <cbc:UBLVersionID t-esc="version_id"/>
                        <t t-foreach="[1, 2, 3, 4]" t-as="value">
                            Oasis <cac:Test t-esc="value"/>
                        </t>
                    </Invoice>
                </t>
            """
        })

        expected_result = etree.fromstring("""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                <cbc:UBLVersionID>1.0</cbc:UBLVersionID>

                    Oasis <cac:Test>1</cac:Test>

                    Oasis <cac:Test>2</cac:Test>

                    Oasis <cac:Test>3</cac:Test>

                    Oasis <cac:Test>4</cac:Test>

            </Invoice>
        """)

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id, {'version_id': 1.0})), expected_result)

    def test_render_static_xml_with_namespaced_attributes(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>
                </t>
            """
        })

        expected_result = etree.fromstring("""<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>""")

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_dynamic_xml_with_namespaced_attributes(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd" t-esc="'abc'"/>
                </t>
            """
        })

        expected_result = etree.fromstring("""<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>""")

        self.assertEqual(etree.fromstring(self.env['ir.qweb']._render(view1.id)), expected_result)

    def test_render_static_xml_with_t_call(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <cac:fruit xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                               xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                        <cac:table>
                            <cbc:td>Appel</cbc:td>
                            <cbc:td>Pineappel</cbc:td>
                        </cac:table>
                    </cac:fruit>
                </t>
            """
        })
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy', 'ir.ui.view', %s, 'base')", [view1.id])

        # view2 will t-call view1
        view2 = self.env['ir.ui.view'].create({
            'name': "dummy2",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy2">
                    <root xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                        <cac:line t-foreach="[1, 2]" t-as="i" t-call="base.dummy"/>
                    </root>
                </t>
            """
        })

        result = self.env['ir.qweb']._render(view2.id)
        result_etree = etree.fromstring(result)

        # check that the root tag has all its xmlns
        expected_ns = {
            (None, 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'),
            ('cac', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'),
            ('cbc', 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'),
        }
        self.assertEqual(set(result_etree.nsmap.items()), expected_ns)

        # check that the t-call did its work
        cac_lines = result_etree.findall('.//cac:line', namespaces={'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'})
        self.assertEqual(len(cac_lines), 2)
        self.assertEqual(result.count('Appel'), 2)

        # check that the t-call dit not output again the xmlns declaration
        self.assertEqual(result.count('xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'), 1)

    def test_render_static_xml_with_extension(self):
        """ Test the extension of a view by an xpath expression on a ns prefixed element.
        """
        # primary view
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <root>
                        <h:table xmlns:h="http://www.example.org/table">
                            <h:tr>
                                <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                                <h:td>Bananas</h:td>
                            </h:tr>
                        </h:table>
                    </root>
                </t>
            """
        })
        # extension patching the primary view
        view2 = self.env['ir.ui.view'].create({
            'name': "dummy_ext",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <xpath expr="//{http://www.example.org/table}table/{http://www.example.org/table}tr">
                        <h:td xmlns:h="http://www.example.org/table">Oranges</h:td>
                </xpath>
            """
        })

        expected_result = etree.fromstring("""
            <root>
                <h:table xmlns:h="http://www.example.org/table">
                    <h:tr>
                        <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                        <h:td>Bananas</h:td>
                        <h:td>Oranges</h:td>
                    </h:tr>
                </h:table>
            </root>
        """)

        self.assertEqual(
            etree.fromstring(self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id])._render(view1.id)),
            expected_result
        )

    def test_render_dynamic_xml_with_code_error(self):
        """ Test that, when rendering a template containing a namespaced node
            that evaluates code with errors, the proper exception is raised
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <Invoice xmlns:od="http://odoo.com/od">
                        <od:name t-att-test="'a' + 1"/>
                    </Invoice>
                </t>
            """
        })

        error_msg = None
        try:
            "" + 0
        except TypeError as e:
            error_msg = e.args[0]

        with self.assertRaises(QWebError, msg=error_msg):
            self.env['ir.qweb']._render(view1.id)


    def test_render_static_xml_with_void_element(self):
        """ Test the rendering on a namespaced view with dynamic URI (need default namespace uri).
        """
        tempate = """
            <rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
                <g:brand>Odoo</g:brand>
                <g:link>My Link</g:link>
            </rss>
        """
        expected_result = """
            <rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
                <g:brand>Odoo</g:brand>
                <g:link>My Link</g:link>
            </rss>

        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">%s</t>
            """ % tempate
        })

        rendering = self.env['ir.qweb']._render(view1.id)

        self.assertEqual(etree.fromstring(rendering), etree.fromstring(expected_result))


@tagged('post_install', '-at_install')
class TestQWebBasic(TransactionCase):
    def test_compile_expr(self):
        tests = [
            #pylint: disable=C0326
            # source,                                   values,                         result
            ("1 +2+ 3",                                 {},                             6),
            ("(((1 +2+ 3)))",                           {},                             6),
            ("(1) +(2+ (3))",                           {},                             6),
            ("a == 5",                                  {'a': 5},                       True),
            ("{'a': True}",                             {},                             {'a': True}),
            ("object.count(1)",                         {'object': [1, 2, 1 ,1]},       3),
            ("dict(a=True)",                            {},                             {'a': True}),
            ("fn(a=11, b=22) or a",                     {'a': 1, 'fn': lambda a,b: 0},  1),
            ("fn(a=11, b=22) or a",                     {'a': 1, 'fn': lambda a,b: b},  22),
            ("(lambda a: a)(5)",                        {},                             5),
            ("(lambda a: a[0])([5])",                   {},                             5),
            ("(lambda test: len(test))('aaa')",         {},                             3),
            ("{'a': lambda a: a[0], 'b': 3}['a']([5])", {},                             5),
            ("list(map(lambda a: a[0], r))",            {'r': [(1,11), (2,22)]},        [1, 2]),
            ("z + (head or 'z')",                       {'z': 'a'},                     "az"),
            ("z + (head or 'z')",                       {'z': 'a', 'head': 'b'},        "ab"),
            ("{a:b for a, b in [(1,11), (2, 22)]}",     {},                             {1: 11, 2: 22}),
            ("any({x == 2 for x in [1,2,3]})",          {},                             True),
            ("any({x == 5 for x in [1,2,3]})",          {},                             False),
            ("{x:y for x,y in [('a', 11),('b', 22)]}",  {},                             {'a': 11, 'b': 22}),
            ("[(y,x) for x,y in [(1, 11),(2, 22)]]",    {},                             [(11, 1), (22, 2)]),
            ("(lambda a: a + 5)(x)",                    {'x': 10},                      15),
            ("(lambda a: a + x)(5)",                    {'x': 10},                      15),
            ("sum(x for x in range(4)) + ((x))",        {'x': 10},                      16),
            ("['test_' + x for x in ['a', 'b']]",       {},                             ['test_a', 'test_b']),
            ("""1 and 2 and 0
                or 9""",                                {},                             9),
            ('[x for x in (1,2)]',                      {},                             [1, 2]),  # LOAD_FAST_AND_CLEAR
            ('list(x for x in (1,2))',                  {},                             [1, 2]),  # END_FOR, CALL_INTRINSIC_1
            ('v if v is None else w',                   {'v': False, 'w': 'foo'},       'foo'),  # POP_JUMP_IF_NONE
            ('v if v is not None else w',               {'v': None, 'w': 'foo'},        'foo'),  # POP_JUMP_IF_NOT_NONE
            ('{a for a in (1, 2)}',                     {},                             {1, 2}),  # RERAISE
        ]

        IrQweb = self.env['ir.qweb']
        for expr, q_values, result in tests:
            expr_namespace = IrQweb._compile_expr(expr)

            compiled = compile("""def test(values):\n  values['result'] = %s""" % expr_namespace, '<test>', 'exec')
            globals_dict = IrQweb._IrQweb__prepare_globals()
            values = {}
            unsafe_eval(compiled, globals_dict, values)
            test = values['test']

            test(q_values)
            q_result = dict(q_values, result=result)
            self.assertDictEqual(q_values, q_result, "Should compile: %s" % expr)

    def test_foreach_as_error_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>'''
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            self.assertIn("KeyError: 't-as'", str(e))
            self.assertIn('<t t-foreach="[3, 2, 1]"/>', str(e.qweb))

    def test_foreach_as_error_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>'''
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("KeyError: 't-as'", error)
            self.assertIn('<t t-foreach="[3, 2, 1]" t-as=""/>', error)

    def test_foreach_as_error_3(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="b-2">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>'''
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("The varname 'b-2' can only contain alphanumeric characters and underscores", error)
            self.assertIn('<t t-foreach="[3, 2, 1]" t-as="b-2"/>', error)

    def test_compile_expr_security(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <div>
                    <t t-set="o" t-value="(lambda a=open: a)()"/>
                    <t t-out="o('/etc/passwd').read()"/>
                </div>
            </t>'''
        })
        values = {'other': 'any value'}
        with self.assertRaises(Exception): # NotImplementedError for 'lambda a=open' and Undefined value 'open'.
            self.env['ir.qweb']._render(t.id, values)

    def test_foreach_iter_list(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="item">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>'''
        })
        result = """
                    [0: 3 3]
                    [1: 2 2]
                    [2: 1 1]
        """

        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_foreach_iter_dict(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="iter-dict">
                <t t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as="item">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>'''
        })
        result = """
                    [0: a 3]
                    [1: b 2]
                    [2: c 1]
        """

        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_escaping_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <div t-att-bibi="json.dumps(bibi)">1</div>
                <div t-att-toto="toto">2</div>
            </t>'''
        })
        result = """
                <div bibi="{&#34;a&#34;: &#34;string&#34;, &#34;b&#34;: 1}">1</div>
                <div toto="a&#39;b&#34;c">2</div>
            """
        values = {'json': json_scriptsafe, 'bibi': dict(a='string', b=1), 'toto': "a'b\"c"}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_escaping_2(self):

        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <t t-set="abc"> <t t-if="add_abc"><t t-out="add_abc"/> <span a="b"> | </span></t><t t-out="efg"/> </t>
                <div t-att-abc="abc">123</div>
            </t>'''
        })
        result = """
                <div abc=" &amp;#34;yes&amp;#34; &lt;span a=&#34;b&#34;&gt; | &lt;/span&gt;-efg- ">123</div>
            """
        values = {'add_abc': '"yes"', 'efg': '-efg-'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <div t-attf-bibi="a, b &gt; c &gt; #{d}">1</div>
            </t>'''
        })
        result = """
                <div bibi="a, b &gt; c &gt; a&#39; &gt; b&#34;c">1</div>
            """
        values = {'d': "a' > b\"c"}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <a t-attf-href="/link/#{ url }/#{other and 'sub'}">link</a>
                <a t-attf-href="/link/#{ url }/#{(not other) and 'sub'}">link2</a>
            </t>'''
        })
        result = """
                <a href="/link/odoo/sub">link</a>
                <a href="/link/odoo/">link2</a>
            """
        values = {'url': 'odoo', 'other': True}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_3(self):

        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <div t-attf-abc="abc #{val} { other }">123</div>
            </t>'''
        })
        result = """
                <div abc="abc &#34;yes&#34; { other }">123</div>
            """
        values = {'val': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_no_propagation_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="bibi">
                <div t-foreach="[1, 2]" t-as="v" class="toto"/>
                <t class="remove_me" t-set="data">a</t>
                <div t-out="data"/>
            </t>'''
        })
        result = """
                <div class="toto"></div><div class="toto"></div>
                <div>a</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_no_propagation_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="bibi">
                <section>
                    <div t-foreach="[1, 2]" t-as="v">
                        <span t-att-test="v" t-esc="v_index"/>
                    </div>
                    <div t-foreach="[1, 2]" t-as="v" class="o">
                        <span t-att-test="v" t-esc="v_index"/>
                    </div>
                </section>
            </t>'''
        })
        result = """
                <section>
                    <div>
                        <span test="1">0</span>
                    </div>
                    <div>
                        <span test="2">1</span>
                    </div>
                    <div class="o">
                        <span test="1">0</span>
                    </div>
                    <div class="o">
                        <span test="2">1</span>
                    </div>
                </section>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(etree.fromstring(rendered), etree.fromstring(result))

    def test_set_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="a" t-value="'abc %s' % 1"/>
                <div t-out="a"/>
            </t>'''
        })
        result = """
                <div>abc 1</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="a" t-valuef="abc {{1}}"/>
                <div t-out="a"/>
            </t>'''
        })
        result = """
                <div>abc 1</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_3(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set='{"a": "abc %s" % 1,
                    "b": 2}'/>
                <div t-out="a"/>
            </t>'''
        })
        result = """
                <div>abc 1</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_body_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="abc"> <span a="b"> [%s] </span> </t>
                <div t-att-abc="abc % add_abc">123</div>
            </t>'''
        })
        result = """
                <div abc=" &lt;span a=&#34;b&#34;&gt; [&amp;#34;yes&amp;#34;] &lt;/span&gt; ">123</div>
            """
        values = {'add_abc': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_body_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="abc"> <span a="b"> toto </span> </t>
                <div t-att-abc="'[%s]' % abc">123</div>
                <div class="a1" t-out="abc"/>
                <div class="a2" t-out="'[%s]' % abc"/>
            </t>'''
        })
        result = """
                <div abc="[ &lt;span a=&#34;b&#34;&gt; toto &lt;/span&gt; ]">123</div>
                <div class="a1"> <span a="b"> toto </span> </div>
                <div class="a2">[ &lt;span a=&#34;b&#34;&gt; toto &lt;/span&gt; ]</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def test_set_error_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="" t-value="1"/>
            </t>'''
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("KeyError: 't-set'", error)
            self.assertIn('<t t-set="" t-value="1"/>', error)

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def test_set_error_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="b-2" t-value="1"/>
            </t>'''
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("The varname can only contain alphanumeric characters and underscores", error)
            self.assertIn('<t t-set="b-2" t-value="1"/>', error)

    def test_out(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="out-format"><div t-out="a">Default</div></t>'''
        })
        result = """<div>1</div>"""
        rendered = self.env['ir.qweb']._render(t.id, {'a': 1})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="out-format">
                <t t-set="final_message">Powered by %s%s</t>
                <div t-out="final_message % (a, b and ('-%s' % b) or '')"/>
            </t>'''
        })
        result = """
                <div>Powered by 1-2</div>
        """
        rendered = self.env['ir.qweb']._render(t.id, {'a': 1, 'b': 2})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="set">
                <t t-set="toto">Toto %s</t>
                <t t-set="abc"> <span a="b"> [%s , %s] </span> </t>
                <div t-out="(abc % (add_abc, toto)) % 5">123</div>
            </t>'''
        })
        result = """
                <div> <span a="b"> [&#34;yes&#34; , Toto 5] </span> </div>
            """
        values = {'add_abc': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_3(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-set">
                <t t-set="toto">Toto %s</t>
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(toto + abc) % v">123</div>
            </t>'''
        })
        result = """
                <div>Toto &#34;yes&#34; <span a="b"> a </span> </div>
            """
        values = {'v': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_4(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(v + abc)">123</div>
            </t>'''
        })
        result = """
                <div>&#34;yes&#34; <span a="b"> a </span> </div>
            """
        values = {'v': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_5(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(abc + v)">123</div>
            </t>'''
        })
        result = """
                <div> <span a="b"> a </span> &#34;yes&#34;</div>
            """
        values = {'v': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_6(self):
        # Use str method will use the string value. t-out will escape this str
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(abc.strip() + v)">123</div>
            </t>'''
        })
        result = """
                <div><span a="b"> a </span>&#34;yes&#34;</div>
            """
        values = {'v': '"yes"'}
        rendered = self.env['ir.qweb']._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_escape_text(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy"><root><span t-out="text" t-options-widget="'text'"/></root></t>
            """
        })
        html = self.env['ir.qweb']._render(view1.id, {'text': """a
        b <b>c</b>"""})
        self.assertEqual(html, """<root><span data-oe-type="text" data-oe-expression="text">a<br>
        b &lt;b&gt;c&lt;/b&gt;</span></root>""")

    def test_out_markup(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-out="content"/>
            </t>'''
        })
        result = """
                <div><span>toto</span></div>
        """
        rendered = self.env['ir.qweb']._render(t.id, {})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_default_value(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="out-default">
                <span rows="10" t-out="a">
                    DEFAULT
                    <t t-out="'Text'" />
                </span>
            </t>'''
        })
        result = """
                <span rows="10">Hello</span>
        """
        rendered = self.env['ir.qweb']._render(t.id, {'a': 'Hello'})
        self.assertEqual(str(rendered.strip()), result.strip())

        result = """
                <span rows="10">
                    DEFAULT
                    Text
                </span>
        """
        rendered = self.env['ir.qweb']._render(t.id, {})
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_esc_markup(self):
        # t-esc is equal to t-out
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-esc="content"/>
            </t>'''
        })
        ref = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-out="content"/>
            </t>'''
        })
        rendered = self.env['ir.qweb']._render(t.id, {})
        result = self.env['ir.qweb']._render(ref.id, {})
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_from_body(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-if="abc">123</div>
                <div t-if="not abc">456</div>
            </t>'''
        })
        result = """
                <div>123</div>
            """
        rendered = self.env['ir.qweb']._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_spaces(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="test">
                <div>
                    0
                    <t>1</t>
                    <t t-if="True">2</t>
                    <t>3</t>
                    4
                    <t>5</t>
                    6
                    <t t-if="True">7</t>
                    8
                    <t t-if="False">9</t>
                    10
                    <t t-if="False">11</t>
                    <t t-else="">12</t>
                    13
                </div>
            </t>'''
        })
        result = """
                <div>
                    0
                    1
                    2
                    3
                    4
                    5
                    6
                    7
                    8
                    10
                    12
                    13
                </div>
            """
        rendered = str(self.env['ir.qweb']._render(t.id))
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_comment(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="test">
                <div>
                    <!-- comment 0 -->
                    0
                    <div>1</div>
                    <!-- comment 1 -->
                    <div t-if="True">2 (t-if)</div>
                    <!-- comment 2 -->
                    <div t-else="">3 (t-else)</div>
                    <!-- comment 3 -->
                    <div>4</div>
                    <!-- comment 4 -->
                    <div t-if="False">5 (t-if)</div>
                    <!-- comment 5 -->
                    <div t-else="">6 (t-else)</div>
                    <!-- comment 6 -->
                    <div>7</div>
                </div>
            </t>'''
        })
        result = """
                <div>
                    
                    0
                    <div>1</div>
                    
                    <div>2 (t-if)</div>
                    
                    
                    <div>4</div>
                    
                    <div>6 (t-else)</div>
                    
                    
                    <div>7</div>
                </div>
            """
        rendered = str(self.env['ir.qweb']._render(t.id))
        self.assertEqual(rendered.strip(), result.strip())

    def test_error_message_1(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="test">
                <section>
                    <div t-esc="abc + def">
                        <span>content</span>
                    </div>
                </section>
            </t>'''
        })
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn('<div t-esc="abc + def"/>', error)

    def test_error_message_2(self):
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="test">
                <section>
                    <div t-esc="abc + def + (">
                        <span>content</span>
                    </div>
                </section>
            </t>'''
        })
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn('Can not compile expression', error)
            self.assertIn('<div t-esc="abc + def + ("/>', error)

    def test_error_message_3(self):
        # The format error tells the developer what to do.
        template = '''<section>
                    <div t-esc="1+2">
                        <span>content</span>
                    </div>
                </section>'''
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(template)
        try:
            self.env['ir.qweb']._render(template)
        except QWebError as e:
            self.assertIn('Inline templates must be passed as `etree` documents', str(e))

        template = '''toto <t t-esc="content"/>'''
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(template)
        try:
            self.env['ir.qweb']._render(template)
        except QWebError as e:
            self.assertIn('Inline templates must be passed as `etree` documents', str(e))

    def test_error_message_4(self):
        # Template record view not found.
        with self.assertRaises(MissingError):
            self.env['ir.qweb']._render(-999)
        try:
            self.env['ir.qweb']._render(-999)
        except MissingError as e:
            self.assertIn('Template does not exist or has been deleted', str(e))

        with self.assertRaises(MissingError):
            self.env['ir.qweb']._render('not.wrong_template_xmlid')
        try:
            self.env['ir.qweb']._render('not.wrong_template_xmlid')
        except MissingError as e:
            self.assertIn('Template not found', str(e))

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(False)
        try:
            self.env['ir.qweb']._render(False)
        except QWebError as e:
            self.assertIn('template is required', str(e))

    def test_error_message_5(self):
        # Error not found a first rendering.
        with self.assertRaises(MissingError, msg="Not Found"):
            self.env['ir.qweb']._render(-9999)

    @mute_logger('odoo.addons.base.models.ir_qweb') # warning for template not found
    def test_error_message_6(self):
        # Error not found a second rendering (first rendering with option hide this error).
        html = self.env['ir.qweb']._render(-9999, raise_if_not_found=False)
        self.assertEqual('', html)

        # re try this rendering without any error (use cached method)
        html = self.env['ir.qweb']._render(-9999, raise_if_not_found=False)
        self.assertEqual('', html)

        # re try this rendering but raise (use cached method)
        with self.assertRaises(MissingError, msg="Not Found"):
            self.env['ir.qweb']._render(-9999)

    def test_error_message_7(self):
        # UserError not found a first rendering.
        with self.assertRaises(UserError, msg="Not Found"):
            self.env['ir.qweb']._render(-9999)

    @mute_logger('odoo.addons.base.models.ir_qweb') # warning for template not found
    def test_error_message_8(self):
        # UserError not found a second rendering (first rendering with option hide this error).
        html = self.env['ir.qweb']._render(-9999, raise_if_not_found=False)
        self.assertEqual('', html)

        # re try this rendering without any error (use cached method)
        html = self.env['ir.qweb']._render(-9999, raise_if_not_found=False)
        self.assertEqual('', html)

        # re try this rendering but raise (use cached method)
        with self.assertRaises(UserError, msg="Not Found"):
            self.env['ir.qweb']._render(-9999)

    def test_error_message_9(self):
        target = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.test_qweb_error',
            'arch_db': '''<t t-name="test">
                <section>
                    <div t-out="abc + def">
                        <span>content</span>
                    </div>
                </section>
            </t>'''
        })
        wrap = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'key': 'base.test_qweb_wrap',
            'arch': """<div><t t-call="base.test_qweb_error"/></div>"""
        })
        t = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': """<div><t t-call="base.test_qweb_wrap"/></div>"""
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            self.assertEqual(str(e),
                "Error while rendering the template:\n"
                "    TypeError: unsupported operand type(s) for +: 'NoneType' and 'NoneType'\n"
                "    Template: base.test_qweb_error\n"
               f"    Reference: {target.id}\n"
                "    Path: /t/section/div\n"
                "    Element: <div t-out=\"abc + def\"/>\n"
               f"    From: ({t.id}, '/div/t', '<t t-call=\"base.test_qweb_wrap\"/>')\n"
               f"          ({wrap.id}, '/div/t', '<t t-call=\"base.test_qweb_error\"/>')\n"
               f"          ({target.id}, '/t/section/div', '<div t-out=\"abc + def\"/>')"
            )

    def test_error_message_10(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.test_qweb_error',
            'arch_db': '''<t t-name="test"><section><div t-out="0"/></section></t>'''
        })
        wrap = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'key': 'base.test_qweb_wrap',
            'arch': """<div><t t-call="base.test_qweb_error"><span t-out="abc + def"/></t></div>"""
        })
        t = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': """<div><t t-call="base.test_qweb_wrap"/></div>"""
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(t.id)

        try:
            self.env['ir.qweb']._render(t.id)
        except QWebError as e:
            self.assertEqual(str(e),
                "Error while rendering the template:\n"
                "    TypeError: unsupported operand type(s) for +: 'NoneType' and 'NoneType'\n"
                "    Template: base.test_qweb_wrap\n"
               f"    Reference: {wrap.id}\n"
                "    Path: /div/t/span\n"
                "    Element: <span t-out=\"abc + def\"/>\n"
               f"    From: ({t.id}, '/div/t', '<t t-call=\"base.test_qweb_wrap\"/>')\n"
               f"          ({wrap.id}, '/div/t/span', '<span t-out=\"abc + def\"/>')"
            )

    def test_call_set(self):
        view0 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <table>
                        <tr><td t-out="a"/></tr>
                        <t t-set="a">3</t>
                    </table>
                </t>
            """
        })
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy', 'ir.ui.view', %s, 'base')", [view0.id])

        view1 = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': """
                <t t-name="base.other">
                    <div>
                        <t t-set="a">1</t>
                        <t t-set="b">1</t>
                        <t t-call="base.dummy">
                            <t t-set="b">2</t>
                        </t>
                        <span t-out="a"/>
                        <span t-out="b"/>
                    </div>
                </t>
            """
        })

        result = self.env['ir.qweb']._render(view1.id, {})
        self.assertEqual(etree.fromstring(result), etree.fromstring("""
            <div>
                <table>
                    <tr><td>1</td></tr>
                </table>
                <span>1</span>
                <span>1</span>
            </div>
        """), 'render t-call use lexical scoping, t-call content use independant scoping')

    def test_call_error(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': """
                <t t-name="base.other">
                    <div>
                        <t t-call="base.dummy"/>
                    </div>
                </t>
            """
        })

        with self.assertRaises(MissingError):
            self.env['ir.qweb']._render(view1.id)

        try:
            self.env['ir.qweb']._render(view1.id)
        except MissingError as e:
            error = str(e.qweb)
            self.assertIn("Template not found: 'base.dummy'", error)
            self.assertIn('<t t-call="base.dummy"/>', error)

    def test_call_infinite_recursion(self):
        self.env['ir.ui.view'].create({
            'name': 'dummy',
            'type': 'qweb',
            'key': 'base.dummy',
            'arch_db': '<article><t t-call="base.dummy"/></article>'
        })
        view1 = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': '<div><t t-call="base.dummy"/></div>'
        })

        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render(view1.id)

        try:
            self.env['ir.qweb']._render(view1.id)
        except QWebError as e:
            error = str(e)
            self.assertIn('Qweb template infinite recursion', error)
            self.assertIn("""'/article/t', '<t t-call="base.dummy"/>'""", error)

    def test_call_call_0(self):
        self.env['ir.ui.view'].create({
            'name': 'micro_child',
            'type': 'qweb',
            'key': 'base.micro_child',
            'arch_db': '<article><t t-out="0"/></article>'
        })
        self.env['ir.ui.view'].create({
            'name': 'wrap',
            'type': 'qweb',
            'key': 'base.wrap',
            'arch_db': '<wrap><t t-out="0"/></wrap>'
        })
        self.env['ir.ui.view'].create({
            'name': 'child',
            'type': 'qweb',
            'key': 'base.child',
            'arch_db': '<t t-call="base.wrap"><section><t t-call="base.micro_child"><t t-out="0"/></t></section></t>'
        })
        view1 = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': '<div><t t-call="base.child">test</t></div>'
        })

        result = self.env['ir.qweb']._render(view1.id)
        self.assertEqual(str(result), "<div><wrap><section><article>test</article></section></wrap></div>")

    def test_call_foreach_call(self):
        self.env['ir.ui.view'].create({
            'name': 'child',
            'type': 'qweb',
            'key': 'base.child',
            'arch_db': '<article><t t-out="toto"/></article>'
        })
        self.env['ir.ui.view'].create({
            'name': 'wrap',
            'type': 'qweb',
            'key': 'base.wrap',
            'arch_db': '<wrap><t t-out="0"/></wrap>'
        })
        view1 = self.env['ir.ui.view'].create({
            'name': "other",
            'type': 'qweb',
            'arch': '<t t-call="base.wrap"><div><t t-foreach="[1,2,3]" t-as="toto"><t t-call="base.child">test</t></t></div></t>'
        })

        result = self.env['ir.qweb']._render(view1.id)
        self.assertEqual(str(result), "<wrap><div><article>1</article><article>2</article><article>3</article></div></wrap>")

    def test_render_t_call_propagates_t_lang(self):
        current_lang = 'en_US'
        other_lang = 'fr_FR'

        lang = self.env['res.lang']._activate_lang(other_lang)
        lang.write({
            'decimal_point': '*',
            'thousands_sep': '/'
        })

        view1 = self.env['ir.ui.view'].create({
            'name': "callee",
            'type': 'qweb',
            'arch': """
                <t t-name="base.callee">
                    <t t-esc="9000000.00" t-options="{'widget': 'float', 'precision': 2}" />
                </t>
            """
        })
        self.env['ir.model.data'].create({
            'name': 'callee',
            'model': 'ir.ui.view',
            'module': 'base',
            'res_id': view1.id,
        })

        view2 = self.env['ir.ui.view'].create({
            'name': "calling",
            'type': 'qweb',
            'arch': """
                <t t-name="base.calling">
                    <t t-call="base.callee" t-lang="'%s'" />
                </t>
            """ % other_lang
        })

        rendered = self.env['ir.qweb'].with_context(lang=current_lang)._render(view2.id).strip()
        self.assertEqual(rendered, '9/000/000*00')

    def test_render_barcode(self):
        partner = self.env['res.partner'].create({
            'name': 'bacode_test',
            'barcode': 'test'
        })

        view = self.env['ir.ui.view'].create({
            'name': "a_barcode_view",
            'type': 'qweb',
        })

        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'width': 100, 'height': 30}"/>"""
        rendered = self.env['ir.qweb']._render(view.id, values={'partner': partner}).strip()
        self.assertRegex(rendered, r'<div><img alt="Barcode test" src="data:image/png;base64,\S+"></div>')

        partner.barcode = '4012345678901'
        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'symbology': 'EAN13', 'width': 100, 'height': 30, 'img_style': 'width:100%;', 'img_alt': 'Barcode'}"/>"""
        ean_rendered = self.env['ir.qweb']._render(view.id, values={'partner': partner}).strip()
        self.assertRegex(ean_rendered, r'<div><img style="width:100%;" alt="Barcode" src="data:image/png;base64,\S+"></div>')

        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'symbology': 'auto', 'width': 100, 'height': 30, 'img_style': 'width:100%;', 'img_alt': 'Barcode'}"/>"""
        auto_rendered = self.env['ir.qweb']._render(view.id, values={'partner': partner}).strip()
        self.assertRegex(auto_rendered, r'<div><img style="width:100%;" alt="Barcode" src="data:image/png;base64,\S+"></div>')

    def test_render_comment_tail(self):
        """ Test the rendering of a tail text, near a comment.
        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': "qweb",
            'arch': """
            <t>
                <!-- it is a comment -->
                <!-- it is another comment -->
                Text 1
                <!-- it is still another comment -->
                Text 2
                <t>ok</t>
            </t>
            """
        })
        emptyline = '\n                '
        expected = markupsafe.Markup('Text 1' + emptyline + emptyline + 'Text 2' + emptyline + 'ok')
        self.assertEqual(self.env['ir.qweb']._render(view1.id).strip(), expected)

    def test_render_comments(self):
        """ Test the rendering of comments with and without the
            preserve_comments option.
        """
        comment = '<!-- Hello, world! -->'
        view = self.env['ir.ui.view'].create({
            'name': 'dummy',
            'type': 'qweb',
            'arch': f'<t><p>{comment}</p></t>'
        })
        QWeb = self.env['ir.qweb']
        self.assertEqual(
            QWeb.with_context(preserve_comments=False)._render(view.id),
            markupsafe.Markup('<p></p>'),
            "Should not have the comment")
        self.env.registry.clear_cache('templates')
        self.assertEqual(
            QWeb.with_context(preserve_comments=True)._render(view.id),
            markupsafe.Markup(f'<p>{comment}</p>'),
            "Should have the comment")

    def test_render_processing_instructions(self):
        """ Test the rendering of processing instructions with and without the
            preserve_comments option.
        """
        p_instruction = '<?hello world?>'
        view = self.env['ir.ui.view'].create({
            'name': 'dummy',
            'type': 'qweb',
            'arch': f'<t><p>{p_instruction}</p></t>'
        })
        QWeb = self.env['ir.qweb']
        self.assertEqual(
            QWeb.with_context(preserve_comments=False)._render(view.id),
            markupsafe.Markup('<p></p>'),
            "Should not have the processing instruction")
        self.env.registry.clear_cache('templates')
        self.assertEqual(
            QWeb.with_context(preserve_comments=True)._render(view.id),
            markupsafe.Markup(f'<p>{p_instruction}</p>'),
            "Should have the processing instruction")

    def test_render_widget_contact(self):
        u = self.env['res.users'].create({
            'name': 'Test',
            'login': 'test@example.com',
        })
        u.name = ""
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy"><root><span t-esc="user" t-options='{"widget": "contact", "fields": ["name"]}' /></root></t>
            """
        })
        self.env['ir.qweb']._render(view1.id, {'user': u})  # should not crash

    def test_render_widget_duration_fallback(self):
        self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'pt_BR')]).active = True
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy"><root><span t-esc="3600" t-options='{"widget": "duration", "format": "short"}' /></root></t>
            """
        })
        self.env['ir.qweb'].with_context(lang='pt_BR')._render(view1.id, {})  # should not crash

    def test_render_template_from_file(self):
        expected_result = etree.fromstring(file_open('base/tests/file_template/file_expected_render.xml').read())
        rendered_result = self.env['ir.qweb']._render('base/tests/file_template/templates/file_template.xml', values={
            'document_name': 'Test Document',
            'partner': {
                'name': 'Jerry',
                'forename': 'Khan',
            },
        })
        self.assertEqual(etree.fromstring(rendered_result), expected_result)

    def test_render_template_from_file_special_cases(self):
        self.env['ir.qweb']._render('base/tests/file_template/templates/../templates/file_template.xml', values={
            'document_name': 'Test Document',
            'partner': {
                'name': 'Jerry',
                'forename': 'Khan',
            },
        })

        self.env['ir.qweb']._render('./base/tests//file_template/templates/file_template.xml', values={
            'document_name': 'Test Document',
            'partner': {
                'name': 'Jerry',
                'forename': 'Khan',
            },
        })

        # Check that we cannot bypass the templates subfolder. We should only be able to read file under this specific subfolder
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render('base/tests/file_template/templates/../unreadable_file_template.xml', values={})

        # Check that as above, if we do not have a parent called templates, the file become unreadable for security reasons.
        with self.assertRaises(QWebError):
            self.env['ir.qweb']._render('base/tests/file_template/unreadable_file_template.xml', values={})

    def test_void_element(self):
        view = self.env['ir.ui.view'].create({
            'name': 'master',
            'type': 'qweb',
            'arch_db': '''<t t-name='master'>
                <meta name="1"/>
                <t t-set="data" t-value="1"/>
                <meta groups="base.group_no_one" name="2"/>
                <meta t-if="False" name="3"/>
                <meta t-if="True" name="4"/>
                <span t-out="1"/>
            </t>'''
        })

        result = '''
                <meta name="1"/>
                <meta name="4"/>
                <span>1</span>
            '''
        rendered = self.env['ir.qweb']._render(view.id)

        self.assertEqual(str(rendered).strip(), result.strip())

    def test_space_remove_technical_space_t_foreach(self):
        view = self.env['ir.ui.view'].create({
            'name': 'master',
            'type': 'qweb',
            'arch_db': '''<t t-name='master'>
                    <section>
                        <article t-foreach="[0, 1, 2]" t-as="value" t-esc="value"/>
                        <t t-foreach="[0, 1, 2]" t-as="value">
                            <article t-esc="value"/>
                        </t>
                    </section>
                </t>'''})

        result = '''
                    <section>
                        <article>0</article><article>1</article><article>2</article>
                            <article>0</article>
                            <article>1</article>
                            <article>2</article>
                    </section>'''

        rendered = self.env['ir.qweb']._render(view.id)

        self.assertEqual(str(rendered), result)

    def test_t_foreach_t_call(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.test',
            'arch_db': '''<t t-out="value"/>'''
        })
        view = self.env['ir.ui.view'].create({
            'name': 'master',
            'type': 'qweb',
            'arch_db': '''<t t-name='master'>
                    <t t-set="value" t-value="3"/>
                    a) <t t-call="base.test"/>
                    b) <t t-foreach="[0, 1]" t-as="value"><t t-call="base.test"/>;</t>
                    c) <t t-foreach="[0, 1]" t-as="value" t-call="base.test"/>
                </t>'''
        })

        result = '''
                    a) 3
                    b) 0;1;
                    c) 01
        '''
        rendered = self.env['ir.qweb']._render(view.id)
        self.assertEqual(str(rendered).strip(), result.strip())

    def test_space_remove_technical_all(self):
        test = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name='test'>
                <span t-out="value"/>
            </t>'''
        })
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('test', 'ir.ui.view', %s, 'base')", [test.id])

        view = self.env['ir.ui.view'].create({
            'name': 'master',
            'type': 'qweb',
            'arch_db': '''<t t-name='master'>

                    <section>
                        <meta name="1"/>
                        <t t-set="data" t-value="1"/>
                        <meta groups="base.group_no_one" name="2"/>
                        <meta t-if="False" name="3"/>
                        <meta t-if="True" name="4"/>

                        <article>
                            <t t-foreach="[0, 1]" t-as="value">
                                <t t-call="base.test"/>
                            </t>

                            <t t-if="False">
                                a
                            </t>
                    
                            b

                            <t t-if="True">
                                c <t t-out="1"/>  
                                d
                            </t>
                        </article>


                        <article>
                            <div t-foreach="[0, 1]" t-as="value">
                                <t t-call="base.test"/>
                            </div>

                            <i t-if="False">
                                a
                            </i>
                            <u t-if="False">
                                a
                            </u>
                    
                            b

                            <i t-if="True">
                                c <t t-out="1"/>  
                                d
                            </i>
                        </article>
                    </section>
                </t>'''
        })

        result = '''
                    <section>
                        <meta name="1"/>
                        <meta name="4"/>

                        <article>
                <span>0</span>
                <span>1</span>

                    
                            b

                                c 1  
                                d
                        </article>


                        <article>
                            <div>
                <span>0</span>
                            </div><div>
                <span>1</span>
                            </div>

                    
                            b

                            <i>
                                c 1  
                                d
                            </i>
                        </article>
                    </section>'''

        rendered = self.env['ir.qweb']._render(view.id)
        self.assertEqual(str(rendered), result)


@tagged('post_install', '-at_install')
class TestQwebPerformance(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo.group_ids = cls.env.ref('base.group_user')

    def test_render_queries(self):
        IrUiView = self.env['ir.ui.view']
        header_0 = IrUiView.create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_header_0',
            'arch_db': '''<span>0</span>'''
        })
        IrUiView.create([{
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_header_1',
            'arch_db': '''<span>1</span>'''
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_header',
            'arch_db': f'''<t t-name="base.testing_header">
                <t t-call="{header_0.id}"/>
                <header>header</header>
                <t t-call="base.testing_header_1"/>
            </t>'''
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer_0',
            'arch_db': '''<span>0</span>'''
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer_1',
            'arch_db': '''<span>1</span>'''
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer',
            'arch_db': '''<t t-name="base.testing_footer">
                <t t-call="base.testing_footer_0"/>
                <header>header</header>
                <t t-call="base.testing_footer_1"/>
            </t>'''
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_layout',
            'arch_db': '''<t t-name="base.testing_layout">
                <section>
                    <header><t t-call="base.testing_header"/></header>
                    <article><t t-out="0"/></article>
                    <header><t t-call="base.testing_footer"/></header>
                </section>
            </t>'''
        }])
        view = IrUiView.create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_content',
            'arch_db': '''<t t-call="base.testing_layout"><div><t t-call="base.testing_header_0"/><t t-out="doc.name"/></div></t>'''
        })
        doc = self.env['ir.attachment'].create({
            'name': 'test',
            'type': 'url',
        })

        expected = """
                <section>
                    <header><span>0</span>
                <header>header</header><span>1</span></header>
                    <article><div><span>0</span>%s</div></article>
                    <header><span>0</span>
                <header>header</header><span>1</span></header>
                </section>"""

        env = self.env(user=self.user_demo)

        # warmup
        env['ir.qweb']._render('base.testing_content', {'doc': doc})

        # do not count those fetching queries
        doc.with_env(env).fetch(['name'])
        env.user.fetch(['name'])

        def check(template, name, queries):
            doc.name = name
            init = env.cr.sql_log_count
            value = env['ir.qweb']._render(template, {'doc': doc})
            self.assertEqual(str(value), expected % name)
            self.assertEqual(env.cr.sql_log_count - init, queries, f'Maximum queries: {queries}')

        # 'base.testing_content'
        #     SELECT id + fields from xmlid
        #     SELECT RECURSIVE arch combine
        # 'base.testing_layout', 'base.testing_header_0'
        #     SELECT id + fields from xmlid
        #     SELECT RECURSIVE arch combine => TODO: batch me
        # 'base.testing_header', 'base.testing_footer'
        #     SELECT id + fields from xmlid
        #     SELECT RECURSIVE arch combine => TODO: batch me
        # 'base.testing_header_1', 'base.testing_footer_0', 'base.testing_footer_1'
        #     SELECT id + fields from xmlid
        #     SELECT RECURSIVE arch combine => TODO: batch me

        FIRST_SEARCH_FETCH = 1  # the first "SELECT id + fields from xmlid"
        OTHER_SEARCH_FETCH = 3  # "SELECT id + fields from xmlid"
        ARCH_COMBINE = 4  # SELECT RECURSIVE arch combine

        self.env.registry.clear_cache('templates')
        view.invalidate_model()

        check('base.testing_content', 'test-cold-0', FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8
        check('base.testing_content', 'test-hot-0', 0)
        check('base.testing_content', 'test-hot-1', 0)

        view.invalidate_model()
        check('base.testing_content', 'test-hot-2', 0)
        check(view.id, 'test-hot-id', 0)

        # like 'test-cold-0'
        self.env.registry.clear_cache('templates')
        check(view.id, 'test-cold-id-1', FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        # like 'test-cold-0' the first search query is replaced by a fetching
        self.env.registry.clear_cache('templates')
        view.invalidate_model()
        check(view.id, 'test-cold-id-2', FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        # like 'test-cold-0'
        self.env.registry.clear_cache('templates')
        check('base.testing_content', 'test-cold-1', FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        # like 'test-cold-0'
        self.env.registry.clear_cache('templates')
        check(view.id, 'test-cold-id-3', FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE - 1)  # 7


@tagged('post_install', '-at_install')
class TestQwebCache(TransactionCase):
    def test_render_xml_cache_base(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')

    def test_render_xml_cache_different(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                        <table t-cache="cache_id2">
                            <tr><td><span t-esc="value2[0]"/></td></tr>
                            <tr><td><span t-esc="value2[1]"/></td></tr>
                            <tr><td><span t-esc="value2[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1,),
            'cache_id2': (1,),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache with different cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (2, 5, 6),
            'cache_id2': (2, 5, 5),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>41</span></td></tr>
                    <tr><td><span>42</span></td></tr>
                    <tr><td><span>43</span></td></tr>
                </table>
                <table>
                    <tr><td><span>51</span></td></tr>
                    <tr><td><span>52</span></td></tr>
                    <tr><td><span>53</span></td></tr>
                </table>
            </div>
        """), 'Use different cache id')

    def test_render_xml_cache_contains_nocache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr t-nocache=""><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering add compiled values in cache')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'Next rendering use cache exept for t-nocache=""')

    def test_render_xml_cache_nocache_cache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-esc="value[0]"/></td></tr>
                            <tr>
                                <td>
                                    <table t-nocache="The content is not used, we can put documentation in it." t-cache="cache_id2">
                                        <tr><td><t t-esc="value2[0]"/></td></tr>
                                        <tr><td><t t-esc="value2[1]"/></td></tr>
                                        <tr><td><t t-esc="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'Second rendering (change inside cache id)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering (change main cache id, old cache inside)')

    def test_render_xml_cache_nocache_cache_on_same_tag(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-esc="value[0]"/></td></tr>
                            <tr t-nocache="">
                                <td>
                                    <table t-cache="cache_id2">
                                        <tr><td><t t-esc="value2[0]"/></td></tr>
                                        <tr><td><t t-esc="value2[1]"/></td></tr>
                                        <tr><td><t t-esc="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'Second rendering (change inside cache id)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering (change main cache id, old cache inside)')

    def test_render_xml_dont_use_cache_base(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'Next rendering cannot cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_different(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                        <table t-cache="cache_id2">
                            <tr><td><span t-esc="value2[0]"/></td></tr>
                            <tr><td><span t-esc="value2[1]"/></td></tr>
                            <tr><td><span t-esc="value2[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': 1,
            'cache_id2': 1,
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (2, 5, 6),
            'cache_id2': (2, 5, 5),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>41</span></td></tr>
                    <tr><td><span>42</span></td></tr>
                    <tr><td><span>43</span></td></tr>
                </table>
                <table>
                    <tr><td><span>51</span></td></tr>
                    <tr><td><span>52</span></td></tr>
                    <tr><td><span>53</span></td></tr>
                </table>
            </div>
        """), 'Use different cache id')

    def test_render_xml_dont_use_cache_contains_nocache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr t-nocache=""><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_recursive(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-esc="value[0]"/></td></tr>
                            <tr>
                                <td>
                                    <table t-nocache="" t-cache="cache_id2">
                                        <tr><td><t t-esc="value2[0]"/></td></tr>
                                        <tr><td><t t-esc="value2[1]"/></td></tr>
                                        <tr><td><t t-esc="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>41</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>43</td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_false_recursive(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-esc="value[0]"/></td></tr>
                            <tr t-nocache="">
                                <td>
                                    <table t-cache="cache_id2">
                                        <tr><td><t t-esc="value2[0]"/></td></tr>
                                        <tr><td><t t-esc="value2[1]"/></td></tr>
                                        <tr><td><t t-esc="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(self.env['ir.qweb']._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>41</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>43</td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

        result = etree.fromstring(self.env['ir.qweb']._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_nocache_use_the_root_values(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <t t-set="counter" t-value="counter + 100"/>
                        <article t-nocache=""><t t-out="counter"/></article>
                        <div>cache: <t t-out="counter"/></div>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <section>
                <article>1</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1 (101 != 1: cached t-set should never be applied on root rendering)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <section>
                <article>2</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (102 != 2: cached t-set should never be applied on root rendering)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <section>
                <article>3</article>
                <div>cache: 103</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (103 != 3: cached t-set should never be applied on root rendering)')

    def test_render_xml_nocache_use_the_root_values_and_cached_values(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <t t-set="counter" t-value="counter + 100"/>
                        <article t-nocache="" t-nocache-counter="counter"><t t-out="counter"/></article>
                        <div>cache: <t t-out="counter"/></div>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1 (1 != 101: new cached values should be add to the root rendering)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (102 != 2: cached values should be used)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <section>
                <article>103</article>
                <div>cache: 103</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (3 != 103: new cached values should be add to the root rendering)')

    def test_render_xml_nocache_use_the_root_values_and_cached_values_error(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <article t-nocache="" t-nocache-record="view_record"><t t-out="view_record"/></article>
                    </section>
                </t>
            """
        })

        with self.assertRaisesRegex(QWebError, "The value type of 't-nocache-record' cannot be cached"):
            self.env['ir.qweb'].with_context(is_t_cache_disabled=False)._render(template_page.id, {
                'cache_id': 1,
                'view_record': self.env['ir.ui.view'].search([], limit=1),
            })

    def test_render_xml_cache_with_t_set_out_of_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <t t-set="counter" t-value="counter + 100"/>
                        <section t-cache="cache_id">
                            <article t-nocache=""><t t-out="counter"/></article>
                            <div>cache: <t t-out="counter"/></div>
                        </section>
                    </root>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <section>
                    <article>1</article>
                    <div>cache: 101</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1 (1 != 101: cached t-set should is applied on first rendering)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <section>
                    <article>2</article>
                    <div>cache: 101</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (2 != 102: cached t-set should be applied the template part are rendered every time)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <section>
                    <article>3</article>
                    <div>cache: 103</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (3 != 103: cached t-set should applied because the new cache key is created)')

    def test_render_xml_cache_with_t_set_in_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <section t-cache="cache_id">
                            <t t-set="counter" t-value="counter + 100"/>
                            <article t-nocache=""><t t-out="counter"/></article>
                            <div>cache: <t t-out="counter"/></div>
                        </section>
                        <div>out of cache: <t t-out="counter"/></div>
                    </root>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <section>
                    <article>1</article>
                    <div>cache: 101</div>
                </section>
                <div>out of cache: 1</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <section>
                    <article>2</article>
                    <div>cache: 101</div>
                </section>
                <div>out of cache: 2</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <section>
                    <article>3</article>
                    <div>cache: 103</div>
                </section>
                <div>out of cache: 3</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_cache_with_t_set_wrap_t_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <cache_1 t-cache="cache_1">
                        <t t-set="a">
                            <cache_2 t-cache="cache_2">
                                <t t-set="counter" t-value="counter + 100"/>
                                <nocache t-nocache="" class="no_cache"><t t-out="counter"/></nocache>
                                <div>cache: <t t-out="counter"/></div>
                            </cache_2>
                            <nocache t-nocache="" class="no_cache"><t t-out="counter * 10"/></nocache>
                        </t>
                        <div>
                            <t t-out="a"/>
                        </div>
                    </cache_1>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_1': 1,
            'cache_2': 1,
            'counter': 1,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">1</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">10</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_1': 2,
            'cache_2': 1,
            'counter': 2,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">2</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">20</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'cache_1': 2,
            'cache_2': 3,
            'counter': 3,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">2</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">20</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

        render = IrQweb._render(template_page.id, {
            'cache_1': 3,
            'cache_2': 3,
            'counter': 3,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">3</nocache>
                        <div>cache: 103</div>
                    </cache_2>
                    <nocache class="no_cache">30</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 4')

    def test_render_xml_t_set_wrap_t_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <t t-set="a">
                            <section t-cache="cache_id">
                                <t t-set="counter" t-value="counter + 100"/>
                                <article t-nocache="" class="no_cache"><t t-out="counter"/></article>
                                <div>cache: <t t-out="counter"/></div>
                            </section>
                            <footer t-nocache="" class="no_cache"><t t-out="counter * 10"/></footer>
                        </t>
                        <div>
                            <t t-out="a"/>
                        </div>
                    </root>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">1</article>
                        <div>cache: 101</div>
                    </section>
                    <footer class="no_cache">10</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">2</article>
                        <div>cache: 101</div>
                    </section>
                    <footer class="no_cache">20</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">3</article>
                        <div>cache: 103</div>
                    </section>
                    <footer class="no_cache">30</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_nocache_in_cache_in_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <section t-cache="key1">
                            <span t-out="val"/>
                            <article t-cache="key2">
                                <span t-nocache="" t-out="val"/>
                            </article>
                        </section>
                    </root>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (1,),
            'val': 1,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>1</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (1,),
            'val': 2,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>2</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (2,),
            'val': 3,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>3</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_nocache_in_nocache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>(counter + 100)
                        <t t-out="counter"/>
                        <nocache t-nocache="wrap cache_b">
                            <t t-set="counter" t-value="counter + 10"/>(counter + 10)
                            <t t-out="counter"/>
                            <cache_b t-cache="cache_b">
                                <t t-out="counter"/>
                                <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                                <nocache t-nocache=""><t t-out="counter"/></nocache>
                            </cache_b>
                        </nocache>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    11
                    <cache_b>
                        11
                        <nocache_value>11</nocache_value>
                        <nocache>1</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    12
                    <cache_b>
                        11
                        <nocache_value>11</nocache_value>
                        <nocache>2</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    13
                    <cache_b>
                        13
                        <nocache_value>13</nocache_value>
                        <nocache>3</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
        })
        result = """
            <cache_a>(counter + 100)
                104
                <nocache>(counter + 10)
                    14
                    <cache_b>
                        13
                        <nocache_value>13</nocache_value>
                        <nocache>4</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_alone(self):
        """ t-nocache without any parented t-cache is ignored"""
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section>
                        <t t-set="counter" t-value="counter + 100"/>
                        <t t-out="counter"/>
                        <nocache t-nocache="">
                            <t t-set="counter" t-value="counter + 10"/>
                            <t t-out="counter"/>
                        </nocache>
                        <t t-out="counter"/>
                        <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                        <nocache t-nocache=""><t t-out="counter"/></nocache>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'counter': 1,
        })
        result = """
            <section>
                101
                <nocache>
                    111
                </nocache>
                111
                <nocache_value>111</nocache_value>
                <nocache>111</nocache>
            </section>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'counter': 2,
        })
        result = """
            <section>
                102
                <nocache>
                    112
                </nocache>
                112
                <nocache_value>112</nocache_value>
                <nocache>112</nocache>
            </section>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call_simple(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '''
                        <nocache t-nocache="">
                            <cache_b t-cache="cache_b">
                                <div><t t-out="counter"/></div>
                                <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                                <nocache t-nocache=""><t t-out="counter"/></nocache>
                            </cache_b>
                        </nocache>
            '''
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>
                        <div><t t-out="counter"/></div>
                        <t t-call="base.testing_callee"/>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>1</div>
                        <nocache_value>1</nocache_value>
                        <nocache>1</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>1</div>
                        <nocache_value>1</nocache_value>
                        <nocache>2</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>3</div>
                        <nocache_value>3</nocache_value>
                        <nocache>3</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
        })
        result = """
            <cache_a>
                <div>104</div><nocache>
                    <cache_b>
                        <div>3</div>
                        <nocache_value>3</nocache_value>
                        <nocache>4</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee_1',
            'arch_db': '''<nocache_value t-nocache="" t-nocache-a="counter">cache:<t t-out="a"/> val:<t t-out="val"/></nocache_value>'''
        })
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee_2',
            'arch_db': '''<nocache t-nocache=""><t t-out="counter"/></nocache>'''
        })
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '''
                        <nocache t-nocache="">
                            <cache_b t-cache="cache_b">
                                <t t-out="counter"/>
                                <t t-call="base.testing_callee_1"/>
                                <t t-call="base.testing_callee_2"/>
                            </cache_b>
                        </nocache>
            '''
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>
                        <t t-out="counter"/>
                        <t t-call="base.testing_callee"/>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
            'val': 1,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        1<nocache_value>cache:1 val:1</nocache_value><nocache>1</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
            'val': 2,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        1<nocache_value>cache:1 val:2</nocache_value><nocache>2</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
            'val': 3,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        3<nocache_value>cache:3 val:3</nocache_value><nocache>3</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
            'val': 4,
        })
        result = """
            <cache_a>
                104<nocache>
                    <cache_b>
                        3<nocache_value>cache:3 val:4</nocache_value><nocache>4</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call_0(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '<callee><t t-out="0"/></callee>'
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <t t-set="counter" t-value="counter + 100"/>
                    <cache t-cache="cache_a">
                        <t t-call="base.testing_callee">
                            <counter><t t-out="counter"/></counter>
                            <nocache><t t-nocache="" t-out="counter"/></nocache>
                        </t>
                    </cache>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'counter': 1,
        })

        result = """
            <cache><callee>
                    <counter>101</counter>
                    <nocache>1</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'counter': 2,
        })
        result = """
            <cache><callee>
                    <counter>101</counter>
                    <nocache>2</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'counter': 3,
        })
        result = """
            <cache><callee>
                    <counter>103</counter>
                    <nocache>3</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_conditional_cache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id if condition else None" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'condition': True, 'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'condition': True, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')


        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')

    def test_render_xml_cache_and_inherit_view(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="True" class="toto">
                        <table>
                            <tr><td><span t-esc="value[0]"/></td></tr>
                            <tr><td><span t-esc="value[1]"/></td></tr>
                            <tr><td><span t-esc="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        # t-cache value can be an interable then we can add value as a tuple (without parenthesis)
        view2 = self.env['ir.ui.view'].create({
            'name': 'Child View',
            'mode': 'extension',
            'inherit_id': view1.id,
            'arch': '''
                <xpath expr="//div[@t-cache]" position="attributes">
                    <attribute name="t-cache" add="company,value[0]" remove="True," separator=","/>
                </xpath>
            ''',
        })

        IrQweb = self.env['ir.qweb'].with_context(use_qweb_t_cache=True)

        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view2.id, {'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering create cache from company and the value 1')

        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view2.id, {'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering create cache from company and the value 10')

    def test_render_nodb(self):
        """ Render an html page without db ans wihtout registry
        """
        expected = dedent("""
            <html>
                <head>
                    <title>Odoo</title>
                </head>
                <body>
                    <section class="toto">
                        <div>3</div>
                    </section>
                </body>
            </html>
        """).strip()

        templates = {
            'html': html.document_fromstring("""
                <html t-name="html">
                    <head>
                        <title>Odoo</title>
                    </head>
                    <body>
                        <section class="toto">
                            <t t-call="content"/>
                        </section>
                    </body>
                </html>
            """),
            'content': html.fragment_fromstring("""
                <t t-name="content">
                        <div><t t-out="val"/></div>
                </t>
            """)
        }
        def load(template_name):
            return (templates[template_name], template_name)
        rendering = render('html', {'val': 3}, load).strip()

        self.assertEqual(html.document_fromstring(rendering), html.document_fromstring(expected))
