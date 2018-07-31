# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import json
import os.path
import re

from lxml import etree

from odoo.modules import get_module_resource
from odoo.tests.common import TransactionCase
from odoo.addons.base.ir.ir_qweb import QWebException
from odoo.tools import misc, ustr


class TestQWebTField(TransactionCase):
    def setUp(self):
        super(TestQWebTField, self).setUp()
        self.env_branding = self.env(context={'inherit_branding': True})
        self.engine = self.env_branding['ir.qweb']

    def test_trivial(self):
        field = etree.Element('span', {'t-field': u'company.name'})
        company = self.env['res.company'].create({'name': "My Test Company"})

        result = self.engine.render(field, {'company': company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring(u'<span data-oe-model="res.company" data-oe-id="%d" '
                  u'data-oe-field="name" data-oe-type="char" '
                  u'data-oe-expression="company.name">%s</span>' % (
                company.id,
                u"My Test Company",
            )),
        )

    def test_i18n(self):
        field = etree.Element('span', {'t-field': u'company.name'})
        s = u"Testing «ταБЬℓσ»: 1<2 & 4+1>3, now 20% off!"
        company = self.env['res.company'].create({'name': s})

        result = self.engine.render(field, {'company': company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring(u'<span data-oe-model="res.company" data-oe-id="%d" '
                  u'data-oe-field="name" data-oe-type="char" '
                  u'data-oe-expression="company.name">%s</span>' % (
                company.id,
                misc.html_escape(s),
            )),
        )

    def test_reject_crummy_tags(self):
        field = etree.Element('td', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(QWebException, r'^RTE widgets do not work correctly'):
            self.engine.render(field, {'company': None})

    def test_reject_t_tag(self):
        field = etree.Element('t', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(QWebException, r'^t-field can not be used on a t element'):
            self.engine.render(field, {'company': None})


class TestQWebNS(TransactionCase):
    def test_render_static_xml_with_namespace(self):
        """ Test the rendering on a namespaced view with no static content. The resulting string should be untouched.
        """
        expected_result = u"""
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
            'arch': u"""
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(view1.render()), etree.fromstring(expected_result))

    def test_render_static_xml_with_namespace_2(self):
        """ Test the rendering on a namespaced view with no static content. The resulting string should be untouched.
        """
        expected_result = u"""
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
            'arch': u"""
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(view1.render()), etree.fromstring(expected_result))

    def test_render_static_xml_with_useless_distributed_namespace(self):
        """ Test that redundant namespaces are stripped upon rendering.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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

        expected_result = etree.fromstring(u"""
            <root>
                <h:table xmlns:h="http://www.example.org/table">
                    <h:tr>
                        <h:td xmlns:h="http://www.w3.org/TD/html4/">Apples</h:td>
                        <h:td>Bananas</h:td>
                    </h:tr>
                </h:table>
            </root>
        """)

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_static_xml_with_namespace_3(self):
        expected_result = u"""
            <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd"></cfdi:Comprobante>
        """

        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">%s</t>
            """ % expected_result
        })

        self.assertEqual(etree.fromstring(view1.render()), etree.fromstring(expected_result))

    def test_render_dynamic_xml_with_namespace_t_esc(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-esc attribute correctly
        handles the t-esc attribute and keep the ns declaration.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-esc="'test'"/>
                </t>
            """
        })

        expected_result = etree.fromstring(u"""<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">test</Invoice>""")

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_dynamic_xml_with_namespace_t_esc_with_useless_distributed_namespace(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-esc attribute correctly
        handles the t-esc attribute and keep the ns declaration, and distribute correctly the ns declaration to its children.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-attf-test="test">
                        <cac:Test xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">blabla</cac:Test>
                    </Invoice>
                </t>
            """
        })

        expected_result = etree.fromstring(u"""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" test="test">
                <cac:Test>blabla</cac:Test>
            </Invoice>
        """)

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_dynamic_xml_with_namespace_t_attf(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-attf attribute correctly
        handles the t-attf attribute and keep the ns declaration.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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

        expected_result = etree.fromstring(u"""
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

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_dynamic_xml_with_namespace_t_attf_with_useless_distributed_namespace(self):
        """ Test that rendering a template containing a node having both an ns declaration and a t-attf attribute correctly
        handles the t-attf attribute and that redundant namespaces are stripped upon rendering.
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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

        expected_result = etree.fromstring(u"""
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

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_dynamic_xml_with_namespace_2(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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

        expected_result = etree.fromstring(u"""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                <cbc:UBLVersionID>1.0</cbc:UBLVersionID>

                    Oasis <cac:Test>1</cac:Test>

                    Oasis <cac:Test>2</cac:Test>

                    Oasis <cac:Test>3</cac:Test>

                    Oasis <cac:Test>4</cac:Test>

            </Invoice>
        """)

        self.assertEqual(etree.fromstring(view1.render({'version_id': 1.0})), expected_result)

    def test_render_static_xml_with_namespaced_attributes(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>
                </t>
            """
        })

        expected_result = etree.fromstring(u"""<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>""")

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_dynamic_xml_with_namespaced_attributes(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd" t-esc="'abc'"/>
                </t>
            """
        })

        expected_result = etree.fromstring("""<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>""")

        self.assertEqual(etree.fromstring(view1.render()), expected_result)

    def test_render_static_xml_with_t_call(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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
            'arch': u"""
                <t t-name="base.dummy2">
                    <root xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                        <cac:line t-foreach="[1, 2]" t-as="i" t-call="base.dummy"/>
                    </root>
                </t>
            """
        })

        result = view2.render()
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
        self.assertEqual(result.count(b'Appel'), 2)

        # check that the t-call dit not output again the xmlns declaration
        self.assertEqual(result.count(b'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'), 1)

    def test_render_static_xml_with_extension(self):
        """ Test the extension of a view by an xpath expression on a ns prefixed element.
        """
        # primary view
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
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
            'arch': u"""
                <xpath expr="//{http://www.example.org/table}table/{http://www.example.org/table}tr">
                        <h:td xmlns:h="http://www.example.org/table">Oranges</h:td>
                </xpath>
            """
        })

        expected_result = etree.fromstring(u"""
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
            etree.fromstring(view1.with_context(check_view_ids=[view1.id, view2.id]).render()),
            expected_result
        )

    def test_render_dynamic_xml_with_code_error(self):
        """ Test that, when rendering a template containing a namespaced node
            that evaluates code with errors, the proper exception is raised
        """
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy">
                    <Invoice xmlns:od="http://odoo.com/od">
                        <od:name t-att-test="'a' + 1"/>
                    </Invoice>
                </t>
            """
        })

        try:
            "" + 0
        except TypeError as e:
            error_msg = e.args[0]

        with self.assertRaises(QWebException, msg=error_msg):
            view1.render()


from copy import deepcopy
class FileSystemLoader(object):
    def __init__(self, path):
        # TODO: support multiple files #add_file() + add cache
        self.path = path
        self.doc = etree.parse(path).getroot()

    def __iter__(self):
        for node in self.doc:
            name = node.get('t-name')
            if name:
                yield name

    def __call__(self, name, options):
        for node in self.doc:
            if node.get('t-name') == name:
                root = etree.Element('templates')
                root.append(deepcopy(node))
                arch = etree.tostring(root, encoding='unicode')
                return arch


class TestQWeb(TransactionCase):
    matcher = re.compile(r'^qweb-test-(.*)\.xml$')

    @classmethod
    def get_cases(cls):
        path = cls.qweb_test_file_path()
        return (
            cls("test_qweb_{}".format(cls.matcher.match(f).group(1)))
            for f in os.listdir(path)
            # js inheritance
            if f != 'qweb-test-extend.xml'
            if cls.matcher.match(f)
        )

    @classmethod
    def qweb_test_file_path(cls):
        return os.path.dirname(get_module_resource('web', 'static', 'lib', 'qweb', 'qweb2.js'))

    def __getattr__(self, item):
        if not item.startswith('test_qweb_'):
            raise AttributeError("No {} on {}".format(item, self))

        f = 'qweb-test-{}.xml'.format(item[10:])
        path = self.qweb_test_file_path()

        return lambda: self.run_test_file(os.path.join(path, f))

    def run_test_file(self, path):
        doc = etree.parse(path).getroot()
        loader = FileSystemLoader(path)
        qweb = self.env['ir.qweb']
        for template in loader:
            if not template or template.startswith('_'):
                continue
            param = doc.find('params[@id="{}"]'.format(template))
            # OrderedDict to ensure JSON mappings are iterated in source order
            # so output is predictable & repeatable
            params = {} if param is None else json.loads(param.text, object_pairs_hook=collections.OrderedDict)

            result = doc.find('result[@id="{}"]'.format(template)).text
            self.assertEqual(
                qweb.render(template, values=params, load=loader).strip(),
                (result or u'').strip().encode('utf-8'),
                template
            )

def load_tests(loader, suite, _):
    # can't override TestQWeb.__dir__ because dir() called on *class* not
    # instance
    suite.addTests(TestQWeb.get_cases())
    return suite
