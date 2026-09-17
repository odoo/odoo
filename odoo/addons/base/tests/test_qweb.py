import ast
import base64
import threading
from unittest.mock import patch

import markupsafe
from lxml import etree

from odoo.exceptions import MissingError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, skip_if_dev_mode
from odoo.tools import file_open, misc, mute_logger
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.rendering_tools import QWebError
from odoo.tools.translate import xml_term_adapter

from odoo.addons.base.models.ir_qweb import (
    ELEMENT_MARKER_REGEXP,
    CompileContext,
    QwebCallParameters,
    QwebContent,
    _StandaloneEnv,
    _StandaloneQweb,
    format_attributes,
    qweb_json,
    render,
)
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

unsafe_eval = eval  # noqa: S307  runs QWeb compiler output (_compile_expr, _compile_format)


@tagged("post_install", "-at_install")
class TestQWebTField(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env_branding = self.env(context={"inherit_branding": True})
        self.engine = self.env_branding["ir.qweb"]

    def test_trivial(self):
        field = etree.Element("span", {"t-field": "company.name"})
        company = self.env["res.company"].create({"name": "My Test Company"})

        result = self.engine._render(field, {"company": company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring(
                '<span data-oe-model="res.company" data-oe-id="%d" '
                'data-oe-field="name" data-oe-type="char" '
                'data-oe-expression="company.name">%s</span>'
                % (
                    company.id,
                    "My Test Company",
                )
            ),
        )

    def test_i18n(self):
        field = etree.Element("span", {"t-field": "company.name"})
        s = "Testing «ταБЬℓσ»: 1<2 & 4+1>3, now 20% off!"
        company = self.env["res.company"].create({"name": s})

        result = self.engine._render(field, {"company": company})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring(
                '<span data-oe-model="res.company" data-oe-id="%d" '
                'data-oe-field="name" data-oe-type="char" '
                'data-oe-expression="company.name">%s</span>'
                % (
                    company.id,
                    misc.html_escape(s),
                )
            ),
        )

    def test_reject_crummy_tags(self):
        field = etree.Element("td", {"t-field": "company.name"})

        with self.assertRaisesRegex(QWebError, r"QWeb widgets do not work correctly"):
            self.engine._render(field, {"company": None})

    def test_reject_t_tag(self):
        field = etree.Element("t", {"t-field": "company.name"})

        with self.assertRaisesRegex(
            QWebError, r"t-field can not be used on a t element"
        ):
            self.engine._render(field, {"company": None})

    def test_render_t_options(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy"><root><span t-esc="5" t-options="{'widget': 'char'}" t-options-widget="'float'" t-options-precision="4"/></root></t>
            """,
            }
        )
        text = etree.fromstring(self.env["ir.qweb"]._render(view1.id)).find("span").text
        self.assertEqual(text, "5.0000")

    def test_render_t_call_options_retrocompat(self):
        self.env["ir.ui.view"].create(
            {
                "name": "qweb_t1_callee",
                "key": "base.qweb_t1_callee",
                "type": "qweb",
                "arch": """<t t-name="base.qweb_t1_callee"><span>CALLEE</span></t>""",
            }
        )
        caller = self.env["ir.ui.view"].create(
            {
                "name": "qweb_t1_caller",
                "key": "base.qweb_t1_caller",
                "type": "qweb",
                "arch": """<t t-name="base.qweb_t1_caller"><t t-call="base.qweb_t1_callee" t-call-options="{}"/></t>""",
            }
        )
        rendered = self.env["ir.qweb"]._render(caller.id)
        self.assertIn("CALLEE", rendered)

    def test_xss_breakout(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <root>
                        <script type="application/javascript">
                            var s = <t t-esc="json.dumps({'key': malicious})"/>;
                        </script>
                    </root>
                </t>
            """,
            }
        )
        rendered = self.env["ir.qweb"]._render(
            view.id,
            {"malicious": '1</script><script>alert("pwned")</script><script>'},
        )
        self.assertIn("alert", rendered, "%r doesn't seem to be rendered" % rendered)
        doc = etree.fromstring(rendered)
        self.assertEqual(len(doc.xpath("//script")), 1)

    def test_default_value(self):
        Partner = self.env["res.partner"]
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="out-field-default">
                <div t-field="record.name">
                    DEFAULT
                    <t t-out="'Text'" />
                </div>
            </t>""",
            }
        )

        result = """
                <div>My Company</div>
        """
        rendered = self.env["ir.qweb"]._render(
            t.id, {"record": Partner.new({"name": "My Company"})}
        )
        self.assertEqual(str(rendered.strip()), result.strip(), "")

        result = """
                <div></div>
        """
        rendered = self.env["ir.qweb"]._render(
            t.id, {"record": Partner.new({"name": ""})}
        )
        self.assertEqual(str(rendered.strip()), result.strip())

        result = """
                <div>
                    DEFAULT
                    Text
                </div>
        """
        rendered = self.env["ir.qweb"]._render(t.id, {"record": Partner.new({})})
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_no_value_no_default_value(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="out-field-default">
                <div t-field="record.name"/>
            </t>""",
            }
        )
        result = """
                <div data-oe-xpath="/t[1]/div[1]" data-oe-model="res.partner" data-oe-field="name" data-oe-type="char" data-oe-expression="record.name"></div>
        """
        rendered = (
            self.env["ir.qweb"]
            .with_context(inherit_branding=True)
            ._render(
                t.id,
                {
                    "record": self.env["res.partner"].new({}),
                },
            )
        )
        self.assertEqual(str(rendered.strip()), result.strip())


@tagged("post_install", "-at_install")
class TestQWebNS(TransactionCase):
    def test_render_static_xml_with_namespace(self):
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

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % expected_result,
            }
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            etree.fromstring(expected_result),
        )

    def test_render_static_xml_with_namespace_2(self):
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

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % expected_result,
            }
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            etree.fromstring(expected_result),
        )

    def test_render_static_xml_with_useless_distributed_namespace(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
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
            """,
            }
        )

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

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_static_xml_with_namespace_3(self):
        expected_result = """
            <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd"></cfdi:Comprobante>
        """

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % expected_result,
            }
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            etree.fromstring(expected_result),
        )

    def test_render_static_xml_with_namespace_dynamic(self):
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

        values = {
            "h1": "http://www.example.org/table",
            "h2": "http://www.w3.org/TD/html4/",
        }

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % tempate,
            }
        )

        rendering = self.env["ir.qweb"]._render(view1.id, values)

        self.assertEqual(
            etree.fromstring(rendering),
            etree.fromstring(expected_result % values),
        )

    def test_render_static_xml_with_namespace_dynamic_2(self):
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

        values = {
            "h1": "http://www.example.org/table",
            "h2": "http://www.w3.org/TD/html4/",
            "f": "http://www.example.org/furniture",
        }

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % tempate,
            }
        )

        rendering = self.env["ir.qweb"]._render(view1.id, values)

        self.assertEqual(
            etree.fromstring(rendering),
            etree.fromstring(expected_result % values),
        )

    def test_render_dynamic_xml_with_namespace_t_esc(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-esc="'test'"/>
                </t>
            """,
            }
        )

        expected_result = etree.fromstring(
            """<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">test</Invoice>"""
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_dynamic_xml_with_namespace_t_esc_with_useless_distributed_namespace(
        self,
    ):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" t-attf-test="test">
                        <cac:Test xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">blabla</cac:Test>
                    </Invoice>
                </t>
            """,
            }
        )

        expected_result = etree.fromstring("""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" test="test">
                <cac:Test>blabla</cac:Test>
            </Invoice>
        """)

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_dynamic_xml_with_namespace_t_attf(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
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
            """,
            }
        )

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

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_dynamic_xml_with_namespace_t_attf_with_useless_distributed_namespace(
        self,
    ):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
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
            """,
            }
        )

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

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_dynamic_xml_with_namespace_2(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                        <cbc:UBLVersionID t-esc="version_id"/>
                        <t t-foreach="[1, 2, 3, 4]" t-as="value">
                            Oasis <cac:Test t-esc="value"/>
                        </t>
                    </Invoice>
                </t>
            """,
            }
        )

        expected_result = etree.fromstring("""
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                <cbc:UBLVersionID>1.0</cbc:UBLVersionID>

                    Oasis <cac:Test>1</cac:Test>

                    Oasis <cac:Test>2</cac:Test>

                    Oasis <cac:Test>3</cac:Test>

                    Oasis <cac:Test>4</cac:Test>

            </Invoice>
        """)

        self.assertEqual(
            etree.fromstring(
                self.env["ir.qweb"]._render(view1.id, {"version_id": 1.0})
            ),
            expected_result,
        )

    def test_render_static_xml_with_namespaced_attributes(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>
                </t>
            """,
            }
        )

        expected_result = etree.fromstring(
            """<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>"""
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_dynamic_xml_with_namespaced_attributes(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd" t-esc="'abc'"/>
                </t>
            """,
            }
        )

        expected_result = etree.fromstring(
            """<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd">abc</cfdi:Comprobante>"""
        )

        self.assertEqual(
            etree.fromstring(self.env["ir.qweb"]._render(view1.id)),
            expected_result,
        )

    def test_render_static_xml_with_t_call(self):
        self.env["ir.ui.view"].create(
            {
                "key": "base.dummy",
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <cac:fruit xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                               xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                        <cac:table>
                            <cbc:td>Appel</cbc:td>
                            <cbc:td>Pineappel</cbc:td>
                        </cac:table>
                    </cac:fruit>
                </t>
            """,
            }
        )

        view2 = self.env["ir.ui.view"].create(
            {
                "name": "dummy2",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy2">
                    <root xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                        <cac:line t-foreach="[1, 2]" t-as="i"><t t-call="base.dummy"/></cac:line>
                    </root>
                </t>
            """,
            }
        )

        result = self.env["ir.qweb"]._render(view2.id)
        result_etree = etree.fromstring(result)

        expected_ns = {
            (None, "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"),
            (
                "cac",
                "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            ),
            (
                "cbc",
                "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            ),
        }
        self.assertEqual(set(result_etree.nsmap.items()), expected_ns)

        cac_lines = result_etree.findall(
            ".//cac:line",
            namespaces={
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            },
        )
        self.assertEqual(len(cac_lines), 2)
        self.assertEqual(result.count("Appel"), 2)

        self.assertEqual(
            result.count(
                'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
            ),
            1,
        )

    def test_render_static_xml_with_extension(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
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
            """,
            }
        )
        view2 = self.env["ir.ui.view"].create(
            {
                "name": "dummy_ext",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <xpath expr="//{http://www.example.org/table}table/{http://www.example.org/table}tr">
                        <h:td xmlns:h="http://www.example.org/table">Oranges</h:td>
                </xpath>
            """,
            }
        )

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
            etree.fromstring(
                self.env["ir.qweb"]
                .with_context(check_view_ids=[view1.id, view2.id])
                ._render(view1.id)
            ),
            expected_result,
        )

    def test_render_dynamic_xml_with_code_error(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <Invoice xmlns:od="http://odoo.com/od">
                        <od:name t-att-test="'a' + 1"/>
                    </Invoice>
                </t>
            """,
            }
        )

        error_msg = None
        try:
            _ = "" + 0
        except TypeError as e:
            error_msg = e.args[0]

        with self.assertRaises(QWebError, msg=error_msg):
            self.env["ir.qweb"]._render(view1.id)

    def test_render_static_xml_with_void_element(self):
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

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">%s</t>
            """
                % tempate,
            }
        )

        rendering = self.env["ir.qweb"]._render(view1.id)

        self.assertEqual(etree.fromstring(rendering), etree.fromstring(expected_result))

    def test_default_namespace_t_is_still_the_t_element(self):
        # Under a default namespace <t> is "{ns}t" to lxml; the whitespace
        # rules of t-call, t-set and t-foreach see the <t> element all the same.
        self.env["ir.ui.view"].create(
            {
                "key": "base.ws_callee",
                "name": "ws_callee",
                "type": "qweb",
                "arch": '<t t-name="base.ws_callee"><i>c</i></t>',
            }
        )
        for arch, expected in (
            (
                '<Invoice xmlns="urn:d">text\n    <t t-call="base.ws_callee"/>\n</Invoice>',
                '<Invoice xmlns="urn:d">text<i>c</i>\n</Invoice>',
            ),
            (
                '<Invoice>text\n    <t t-call="base.ws_callee"/>\n</Invoice>',
                "<Invoice>text<i>c</i>\n</Invoice>",
            ),
            (
                '<Invoice xmlns="urn:d">text\n    <t t-set="x" t-value="1"/>\n</Invoice>',
                '<Invoice xmlns="urn:d">text\n</Invoice>',
            ),
            (
                '<Invoice xmlns="urn:d">text\n    <t t-foreach="[1, 2]" t-as="i"><a/></t>\n</Invoice>',
                '<Invoice xmlns="urn:d">text<a></a><a></a>\n</Invoice>',
            ),
        ):
            view = self.env["ir.ui.view"].create(
                {"name": "ws_caller", "type": "qweb", "arch": f"<t>{arch}</t>"}
            )
            self.assertEqual(str(self.env["ir.qweb"]._render(view.id)), expected)

    def test_t_field_on_a_default_namespace_t_is_rejected(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "field_ns_t",
                "type": "qweb",
                "arch": '<t><root xmlns="urn:d"><t t-field="r.name"/></root></t>',
            }
        )
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(view.id, {"r": self.env.user})
        self.assertIn("t-field can not be used on a t element", str(cm.exception))

    def test_attribute_prefix_survives_a_later_default_declaration(self):
        # lxml lists the default namespace after the prefix that shares its
        # URI; the reverse map must never pick the None prefix for an attribute.
        view = self.env["ir.ui.view"].create(
            {
                "name": "dual_ns",
                "type": "qweb",
                "arch": '<t><root xmlns:d="urn:d" xmlns="urn:d" d:k="v" t-att-a="1">x</root></t>',
            }
        )
        rendered = str(self.env["ir.qweb"]._render(view.id))
        self.assertIn(' d:k="v"', rendered)
        self.assertNotIn("None:", rendered)

    def test_xml_prefixed_attributes_keep_their_prefix(self):
        for arch in (
            '<div xml:lang="en">x</div>',
            '<div xml:lang="en" t-att-a="a">x</div>',
            '<div xmlns:y="urn:y" xml:lang="en" y:k="v" t-att-a="a">x</div>',
        ):
            view = self.env["ir.ui.view"].create(
                {"name": "xml_prefix", "type": "qweb", "arch": f"<t>{arch}</t>"}
            )
            rendered = str(self.env["ir.qweb"]._render(view.id, {"a": 1}))
            self.assertIn(' xml:lang="en"', rendered, arch)
            self.assertNotIn("{http://www.w3.org/XML/1998/namespace}", rendered)
            self.assertEqual(etree.fromstring(rendered).text, "x")

    def test_t_call_does_not_redeclare_the_callers_namespace(self):
        self.env["ir.ui.view"].create(
            {
                "key": "base.ns_callee",
                "name": "ns_callee",
                "type": "qweb",
                "arch": """
                <t t-name="base.ns_callee">
                    <y:a xmlns:y="urn:y"><x:b xmlns:x="urn:x">v</x:b></y:a>
                    <y:c xmlns:y="urn:y" t-att-k="1"><x:d xmlns:x="urn:x" t-att-k="2">w</x:d></y:c>
                </t>
                """,
            }
        )
        caller = self.env["ir.ui.view"].create(
            {
                "name": "ns_caller",
                "type": "qweb",
                "arch": """
                <t t-name="base.ns_caller">
                    <root xmlns:x="urn:x"><t t-call="base.ns_callee"/></root>
                </t>
                """,
            }
        )
        rendered = str(self.env["ir.qweb"]._render(caller.id))
        self.assertEqual(rendered.count('xmlns:x="urn:x"'), 1)
        self.assertEqual(rendered.count('xmlns:y="urn:y"'), 2)
        tree = etree.fromstring(rendered)
        self.assertEqual(
            [el.text for el in tree.iter("{urn:x}b", "{urn:x}d")], ["v", "w"]
        )


@tagged("post_install", "-at_install")
class TestQWebBasic(TransactionCase):
    def test_compile_expr(self):
        tests = [
            ("1 +2+ 3", {}, 6),
            ("(((1 +2+ 3)))", {}, 6),
            ("(1) +(2+ (3))", {}, 6),
            ("a == 5", {"a": 5}, True),
            ("{'a': True}", {}, {"a": True}),
            ("object.count(1)", {"object": [1, 2, 1, 1]}, 3),
            ("dict(a=True)", {}, {"a": True}),
            ("fn(a=11, b=22) or a", {"a": 1, "fn": lambda a, b: 0}, 1),
            ("fn(a=11, b=22) or a", {"a": 1, "fn": lambda a, b: b}, 22),
            ("(lambda a: a)(5)", {}, 5),
            ("(lambda a: a[0])([5])", {}, 5),
            ("(lambda test: len(test))('aaa')", {}, 3),
            ("{'a': lambda a: a[0], 'b': 3}['a']([5])", {}, 5),
            ("list(map(lambda a: a[0], r))", {"r": [(1, 11), (2, 22)]}, [1, 2]),
            ("z + (head or 'z')", {"z": "a"}, "az"),
            ("z + (head or 'z')", {"z": "a", "head": "b"}, "ab"),
            ("{a:b for a, b in [(1,11), (2, 22)]}", {}, {1: 11, 2: 22}),
            ("any({x == 2 for x in [1,2,3]})", {}, True),
            ("any({x == 5 for x in [1,2,3]})", {}, False),
            ("{x:y for x,y in [('a', 11),('b', 22)]}", {}, {"a": 11, "b": 22}),
            ("[(y,x) for x,y in [(1, 11),(2, 22)]]", {}, [(11, 1), (22, 2)]),
            ("(lambda a: a + 5)(x)", {"x": 10}, 15),
            ("(lambda a: a + x)(5)", {"x": 10}, 15),
            ("sum(x for x in range(4)) + ((x))", {"x": 10}, 16),
            ("['test_' + x for x in ['a', 'b']]", {}, ["test_a", "test_b"]),
            (
                """1 and 2 and 0
                or 9""",
                {},
                9,
            ),
            ("[x for x in (1,2)]", {}, [1, 2]),
            ("list(x for x in (1,2))", {}, [1, 2]),
            (
                "v if v is None else w",
                {"v": False, "w": "foo"},
                "foo",
            ),
            (
                "v if v is not None else w",
                {"v": None, "w": "foo"},
                "foo",
            ),
            ("{a for a in (1, 2)}", {}, {1, 2}),
            ("(lambda a: a + a)(x)", {"x": 1}, 2),
            ("sum(i for i in range(n))", {"n": 3}, 3),
            ("[i * i for i in range(n)]", {"n": 3}, [0, 1, 4]),
            ("3 + 4 * 5", {}, 23),
            ("None if x else 9", {"x": 0}, 9),
            ("1 if x else 2", {"x": []}, 2),
            ("bool(x) and x + 1", {"x": 5}, 6),
        ]

        IrQweb = self.env["ir.qweb"]
        for expr, q_values, result in tests:
            expr_namespace = IrQweb._compile_expr(expr)

            compiled = compile(
                """def test(values):\n  values['result'] = %s""" % expr_namespace,
                "<test>",
                "exec",
            )
            globals_dict = IrQweb._prepare_globals()
            values = {}
            unsafe_eval(compiled, globals_dict, values)
            test = values["test"]

            test(q_values)
            q_result = dict(q_values, result=result)
            self.assertDictEqual(q_values, q_result, "Should compile: %s" % expr)

    def test_foreach_as_error_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            self.assertIn("KeyError: 't-as'", str(e))
            self.assertIn('<t t-foreach="[3, 2, 1]"/>', str(e.qweb))

    def test_foreach_as_error_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("KeyError: 't-as'", error)
            self.assertIn('<t t-foreach="[3, 2, 1]" t-as=""/>', error)

    def test_foreach_as_error_3(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="b-2">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn(
                "The varname 'b-2' can only contain alphanumeric characters and underscores",
                error,
            )
            self.assertIn('<t t-foreach="[3, 2, 1]" t-as="b-2"/>', error)

    def test_compile_expr_security(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <div>
                    <t t-set="o" t-value="(lambda a=open: a)()"/>
                    <t t-out="o('/etc/passwd').read()"/>
                </div>
            </t>""",
            }
        )
        values = {"other": "any value"}
        with self.assertRaises(Exception):
            self.env["ir.qweb"]._render(t.id, values)

    def test_compile_expr_forbidden(self):
        IrQweb = self.env["ir.qweb"]
        forbidden = [
            "().__class__",
            "''.__class__.__mro__",
            "''.__class__.__mro__[1].__subclasses__()",
            "[].__class__.__base__.__subclasses__()",
            "(lambda f: f.__globals__)(lambda: None)",
            "().__class__.__bases__",
            "__import__('os')",
            "__builtins__",
            "__import__('os').system('echo pwned')",
        ]
        for expr in forbidden:
            with self.assertRaises(Exception, msg="compile should reject: %s" % expr):
                IrQweb._compile_expr(expr)

            view = self.env["ir.ui.view"].create(
                {
                    "name": "forbidden",
                    "type": "qweb",
                    "arch_db": '<t t-name="forbidden"><t t-out="%s"/></t>'
                    % misc.html_escape(expr),
                }
            )
            with self.assertRaises(Exception, msg="render should reject: %s" % expr):
                IrQweb._render(view.id)

    def test_post_processing_att_malicious_scheme(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "malicious-scheme",
                "type": "qweb",
                "arch_db": """<t t-name="malicious-scheme">
                    <a t-att-href="bad"/>
                    <a t-att-href="back"/>
                </t>""",
            }
        )
        rendered = self.env["ir.qweb"]._render(
            view.id,
            {"bad": "javascript:alert(1)", "back": "javascript:history.back()"},
        )
        doc = etree.fromstring("<root>%s</root>" % rendered)
        links = doc.findall("a")
        self.assertEqual(links[0].get("href"), "")
        self.assertEqual(links[1].get("href"), "javascript:history.back()")

    def test_post_processing_att_malicious_scheme_extra_attributes(self):
        qweb = self.env["ir.qweb"]
        for attr in ("href", "src", "action", "formaction", "xlink:href", "data"):
            atts = qweb._post_processing_att(
                "a", {attr: "javascript:alert(1)", "title": "keep"}, is_static=False
            )
            self.assertEqual(atts[attr], "", f"{attr!r} javascript: not scrubbed")
            self.assertEqual(atts["title"], "keep")
        static = qweb._post_processing_att(
            "a", {"xlink:href": "javascript:alert(1)"}, is_static=True
        )
        self.assertEqual(static["xlink:href"], "javascript:alert(1)")
        legit = qweb._post_processing_att(
            "object", {"data": "/web/content/1"}, is_static=False
        )
        self.assertEqual(legit["data"], "/web/content/1")

    def test_qwebcontent_cross_database_guard(self):
        captured = []
        orig_init = QwebContent.__init__

        def capture(self_qc, irQweb, params):
            orig_init(self_qc, irQweb, params)
            captured.append(self_qc)

        view = self.env["ir.ui.view"].create(
            {
                "name": "qc-cross-db",
                "type": "qweb",
                "arch_db": '<t t-name="qc-cross-db">'
                '<t t-set="frag"><b>secret</b></t>'
                "<span>outer</span></t>",
            }
        )
        with patch.object(QwebContent, "__init__", capture):
            self.env["ir.qweb"]._render(view.id, {})
        qc = next((c for c in captured if c.html is None), None)
        self.assertIsNotNone(qc, "no unrendered QwebContent captured")

        thread = threading.current_thread()
        original = getattr(thread, "dbname", None)
        try:
            thread.dbname = self.env.cr.dbname
            qc.html = None
            self.assertIn("secret", str(qc))
            thread.dbname = "some_other_database"
            qc.html = None
            self.assertEqual(str(qc), "")
            if hasattr(thread, "dbname"):
                del thread.dbname
            qc.html = None
            self.assertIn("secret", str(qc))
        finally:
            if original is None:
                if hasattr(thread, "dbname"):
                    del thread.dbname
            else:
                thread.dbname = original

    def test_post_processing_att_control_char_obfuscation(self):
        obfuscations = [
            "java\tscript:alert(1)",
            "java\nscript:alert(1)",
            "java\rscript:alert(1)",
            "java\x00script:alert(1)",
            "java\x01script:alert(1)",
        ]
        view = self.env["ir.ui.view"].create(
            {
                "name": "malicious-scheme-ctrl",
                "type": "qweb",
                "arch_db": """<t t-name="malicious-scheme-ctrl">
                    <a t-foreach="payloads" t-as="p" t-att-href="p" class="danger"/>
                    <a t-att-href="ok" class="safe"/>
                </t>""",
            }
        )
        rendered = self.env["ir.qweb"]._render(
            view.id, {"payloads": obfuscations, "ok": "https://example.com/x"}
        )
        doc = etree.fromstring("<root>%s</root>" % rendered)
        danger = doc.findall(".//a[@class='danger']")
        self.assertEqual(len(danger), len(obfuscations))
        for link, payload in zip(danger, obfuscations, strict=True):
            self.assertEqual(
                link.get("href"),
                "",
                "control-char obfuscation %r was not scrubbed" % payload,
            )
        self.assertEqual(
            doc.find(".//a[@class='safe']").get("href"), "https://example.com/x"
        )

    def test_directives_eval_order_precedence(self):
        order = self.env["ir.qweb"]._get_directive_eval_order()
        self.assertEqual(
            len(order), len(set(order)), "duplicate directive in eval order"
        )
        pos = {name: i for i, name in enumerate(order)}
        pairs = [
            ("elif", "if"),
            ("else", "if"),
            ("foreach", "if"),
            ("as", "foreach"),
            ("if", "call"),
            ("options", "call"),
            ("call", "att"),
            ("tag-open", "set"),
            ("set", "inner-content"),
            ("inner-content", "tag-close"),
        ]
        for earlier, later in pairs:
            self.assertIn(earlier, pos)
            self.assertIn(later, pos)
            self.assertLess(
                pos[earlier],
                pos[later],
                "%r must be evaluated before %r" % (earlier, later),
            )

    def test_tcall_compile_is_memoized_per_render(self):
        self.env["ir.ui.view"].create(
            {
                "name": "memo-child",
                "key": "base.memo_child",
                "type": "qweb",
                "arch_db": """<t t-name="base.memo_child"><span t-out="i"/></t>""",
            }
        )
        parent = self.env["ir.ui.view"].create(
            {
                "name": "memo-parent",
                "key": "base.memo_parent",
                "type": "qweb",
                "arch_db": """<t t-name="base.memo_parent"><div>
                    <t t-foreach="range(count)" t-as="i">
                        <t t-call="base.memo_child"/>
                    </t></div></t>""",
            }
        )
        qweb = self.env["ir.qweb"]
        real_compile = type(qweb)._compile
        calls = []

        def counting_compile(self, template):
            calls.append(template)
            return real_compile(self, template)

        count = 40
        with patch.object(type(qweb), "_compile", counting_compile):
            rendered = qweb._render(parent.id, {"count": count})
        self.assertEqual(rendered.count("<span>"), count)
        self.assertLessEqual(
            len(calls),
            4,
            "t-call compile not memoized: %d _compile calls for %d iterations"
            % (len(calls), count),
        )

    def test_render_etree_tset_body_content(self):
        template = etree.fromstring(
            """<t>
                <t t-foreach="range(3)" t-as="i">
                    <t t-set="blk"><b t-out="i"/>!</t>
                    <span t-out="blk"/>
                </t>
            </t>"""
        )
        rendered = self.env["ir.qweb"]._render(template, {})
        self.assertEqual(rendered.count("<b>"), 3)
        self.assertIn("<b>0</b>!", rendered)
        self.assertIn("<b>2</b>!", rendered)

    def test_raw_stays_unescaped(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "raw-vs-out",
                "type": "qweb",
                "arch_db": """<t t-name="raw-vs-out">
                    <span class="out" t-out="payload"/>
                    <span class="raw" t-raw="payload"/>
                </t>""",
            }
        )
        payload = "<b>bold</b>"
        with mute_logger("odoo.addons.base.models.ir_qweb"):
            rendered = self.env["ir.qweb"]._render(view.id, {"payload": payload})
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", rendered)
        self.assertIn('<span class="raw"><b>bold</b></span>', rendered)

    def test_foreach_iter_list(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="iter-list">
                <t t-foreach="[3, 2, 1]" t-as="item">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>""",
            }
        )
        result = """
                    [0: 3 3]
                    [1: 2 2]
                    [2: 1 1]
        """

        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_foreach_iter_dict(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="iter-dict">
                <t t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as="item">
                    [<t t-esc="item_index"/>: <t t-esc="item"/> <t t-esc="item_value"/>]</t>
            </t>""",
            }
        )
        result = """
                    [0: a 3]
                    [1: b 2]
                    [2: c 1]
        """

        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_foreach_lazy_last_no_leak(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="lazy-last">"""
                """<t t-foreach="gen" t-as="x">"""
                """[<t t-esc="x"/>:<t t-esc="'Y' if x_last else 'N'"/>]</t>"""
                """</t>""",
            }
        )
        rendered = self.env["ir.qweb"]._render(
            t.id, {"gen": (c for c in "ab"), "x_last": "STALE"}
        )
        self.assertEqual(rendered.strip(), "[a:N][b:N]")
        self.assertNotIn("STALE", rendered)

    def test_att_escaping_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <div t-att-bibi="json.dumps(bibi)">1</div>
                <div t-att-toto="toto">2</div>
            </t>""",
            }
        )
        result = """
                <div bibi="{&#34;a&#34;: &#34;string&#34;, &#34;b&#34;: 1}">1</div>
                <div toto="a&#39;b&#34;c">2</div>
            """
        values = {
            "json": json_scriptsafe,
            "bibi": {"a": "string", "b": 1},
            "toto": "a'b\"c",
        }
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_escaping_2(self):

        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <t t-set="abc"> <t t-if="add_abc"><t t-out="add_abc"/> <span a="b"> | </span></t><t t-out="efg"/> </t>
                <div t-att-abc="abc">123</div>
            </t>""",
            }
        )
        result = """
                <div abc=" &amp;#34;yes&amp;#34; &lt;span a=&#34;b&#34;&gt; | &lt;/span&gt;-efg- ">123</div>
            """
        values = {"add_abc": '"yes"', "efg": "-efg-"}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <div t-attf-bibi="a, b &gt; c &gt; #{d}">1</div>
            </t>""",
            }
        )
        result = """
                <div bibi="a, b &gt; c &gt; a&#39; &gt; b&#34;c">1</div>
            """
        values = {"d": "a' > b\"c"}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <a t-attf-href="/link/#{ url }/#{other and 'sub'}">link</a>
                <a t-attf-href="/link/#{ url }/#{(not other) and 'sub'}">link2</a>
            </t>""",
            }
        )
        result = """
                <a href="/link/odoo/sub">link</a>
                <a href="/link/odoo/">link2</a>
            """
        values = {"url": "odoo", "other": True}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_attf_escaping_3(self):

        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-escaping">
                <div t-attf-abc="abc #{val} { other }">123</div>
            </t>""",
            }
        )
        result = """
                <div abc="abc &#34;yes&#34; { other }">123</div>
            """
        values = {"val": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_no_propagation_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="bibi">
                <div t-foreach="[1, 2]" t-as="v" class="toto"/>
                <t class="remove_me" t-set="data">a</t>
                <div t-out="data"/>
            </t>""",
            }
        )
        result = """
                <div class="toto"></div><div class="toto"></div>
                <div>a</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_att_no_propagation_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="bibi">
                <section>
                    <div t-foreach="[1, 2]" t-as="v">
                        <span t-att-test="v" t-esc="v_index"/>
                    </div>
                    <div t-foreach="[1, 2]" t-as="v" class="o">
                        <span t-att-test="v" t-esc="v_index"/>
                    </div>
                </section>
            </t>""",
            }
        )
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
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(etree.fromstring(rendered), etree.fromstring(result))

    def test_set_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="a" t-value="'abc %s' % 1"/>
                <div t-out="a"/>
            </t>""",
            }
        )
        result = """
                <div>abc 1</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="a" t-valuef="abc {{1}}"/>
                <div t-out="a"/>
            </t>""",
            }
        )
        result = """
                <div>abc 1</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_3(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set='{"a": "abc %s" % 1,
                    "b": 2}'/>
                <div t-out="a"/>
            </t>""",
            }
        )
        result = """
                <div>abc 1</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_body_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="abc"> <span a="b"> [%s] </span> </t>
                <div t-att-abc="abc % add_abc">123</div>
            </t>""",
            }
        )
        result = """
                <div abc=" &lt;span a=&#34;b&#34;&gt; [&amp;#34;yes&amp;#34;] &lt;/span&gt; ">123</div>
            """
        values = {"add_abc": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_body_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="abc"> <span a="b"> toto </span> </t>
                <div t-att-abc="'[%s]' % abc">123</div>
                <div class="a1" t-out="abc"/>
                <div class="a2" t-out="'[%s]' % abc"/>
            </t>""",
            }
        )
        result = """
                <div abc="[ &lt;span a=&#34;b&#34;&gt; toto &lt;/span&gt; ]">123</div>
                <div class="a1"> <span a="b"> toto </span> </div>
                <div class="a2">[ &lt;span a=&#34;b&#34;&gt; toto &lt;/span&gt; ]</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_set_body_3(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.test_set_body_3",
                "arch_db": """<t t-name="set">
                <t t-set="a_empty"><t t-out="''"/></t>
                <t t-set="abc"> toto   </t>
                <div t-att-a="abc" t-att-b="abc.strip()" t-att-c="abc[2]" t-att-d="abc[2:4]" t-att-len="len(abc)" t-att-bool="bool(abc)" t-att-bool_empty="str(bool(a_empty))">123</div>
            </t>""",
            }
        )
        result = """
                <div a=" toto   " b="toto" c="o" d="ot" len="8" bool="True" bool_empty="False">123</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(str(rendered.strip()), result.strip())

        for test, res in [
            ("abc.strip()", "toto"),
            ("abc[2]", "o"),
            ("abc[2:4]", "ot"),
            ("len(abc)", 8),
            ("bool(abc)", True),
        ]:
            t.arch_db = (
                """<t t-name="set"><t t-set="abc"> toto   </t><div t-att-a="%s">123</div></t>"""
                % test
            )
            result = """<div a="%s">123</div>""" % res
            rendered = self.env["ir.qweb"]._render(t.id)
            self.assertEqual(str(rendered.strip()), result.strip(), (test, res))

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_set_error_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="" t-value="1"/>
            </t>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("KeyError: 't-set'", error)
            self.assertIn('<t t-set="" t-value="1"/>', error)

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_set_error_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="b-2" t-value="1"/>
            </t>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn(
                "The varname can only contain alphanumeric characters and underscores",
                error,
            )
            self.assertIn('<t t-set="b-2" t-value="1"/>', error)

    def test_out(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="out-format"><div t-out="a">Default</div></t>""",
            }
        )
        result = """<div>1</div>"""
        rendered = self.env["ir.qweb"]._render(t.id, {"a": 1})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="out-format">
                <t t-set="final_message">Powered by %s%s</t>
                <div t-out="final_message % (a, b and ('-%s' % b) or '')"/>
            </t>""",
            }
        )
        result = """
                <div>Powered by 1-2</div>
        """
        rendered = self.env["ir.qweb"]._render(t.id, {"a": 1, "b": 2})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="set">
                <t t-set="toto">Toto %s</t>
                <t t-set="abc"> <span a="b"> [%s , %s] </span> </t>
                <div t-out="(abc % (add_abc, toto)) % 5">123</div>
            </t>""",
            }
        )
        result = """
                <div> <span a="b"> [&#34;yes&#34; , Toto 5] </span> </div>
            """
        values = {"add_abc": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_3(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="toto">Toto %s</t>
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(toto + abc) % v">123</div>
            </t>""",
            }
        )
        result = """
                <div>Toto &#34;yes&#34; <span a="b"> a </span> </div>
            """
        values = {"v": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_4(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(v + abc)">123</div>
            </t>""",
            }
        )
        result = """
                <div>&#34;yes&#34; <span a="b"> a </span> </div>
            """
        values = {"v": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_5(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(abc + v)">123</div>
            </t>""",
            }
        )
        result = """
                <div> <span a="b"> a </span> &#34;yes&#34;</div>
            """
        values = {"v": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_6(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-out="(abc.strip() + v)">123</div>
            </t>""",
            }
        )
        result = """
                <div><span a="b"> a </span>&#34;yes&#34;</div>
            """
        values = {"v": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_format_7(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test-lazy">
                <t t-set="val"><b>TOTO %s</b></t>
                <t t-if="'TOTO' in val">OK</t>
                <a t-out="val"/>
            </t>""".replace("                ", ""),
            }
        )
        result = """
                OK
                <a><b>TOTO %s</b></a>
            """.replace("                ", "")
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_out_format_8(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test-lazy">
                <t t-set="val"><b>TOTO %s</b></t>
                <t t-if="'TOTO' in val">if 'TOTO' in val</t>
                <t t-if="'>' in val">if > in val</t>
                <t t-if="'<b>' in val">if tag in val</t>
                <a t-att-help="val % 1"/>
            </t>""".replace("                ", ""),
            }
        )
        result = """
                if 'TOTO' in val
                if > in val
                if tag in val
                <a help="&lt;b&gt;TOTO 1&lt;/b&gt;"></a>
            """.replace("                ", "")
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_out_format_9(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test-lazy">
                <t t-set="val"><b>TOTO %s</b></t>
                <a t-out="val.replace('T', '_')"/>
            </t>""",
            }
        )
        result = """<a><b>_O_O %s</b></a>"""
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_out_json(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="abc"> <span> a </span> </t>
                <t t-set="props" t-value="{ 'a': 1, 'abc': abc }"/>
                <div t-att-data="json.dumps(props)"/>
            </t>""",
            }
        )
        result = """
                <div data="{&#34;a&#34;: 1, &#34;abc&#34;: &#34; &lt;span&gt; a &lt;/span&gt; &#34;}"></div>
            """
        values = {"v": '"yes"'}
        rendered = self.env["ir.qweb"]._render(t.id, values)
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_out_escape_text(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy"><root><span t-out="text" t-options-widget="'text'"/></root></t>
            """,
            }
        )
        values = {
            "text": """a
        b <b>c</b>"""
        }
        html = self.env["ir.qweb"]._render(view1.id, dict(values))
        self.assertEqual(
            html,
            """<root><span>a<br>
        b &lt;b&gt;c&lt;/b&gt;</span></root>""",
        )
        branded = (
            self.env["ir.qweb"]
            .with_context(inherit_branding=True)
            ._render(view1.id, dict(values))
        )
        self.assertEqual(
            branded,
            """<root><span data-oe-type="text" data-oe-expression="text">a<br>
        b &lt;b&gt;c&lt;/b&gt;</span></root>""",
        )

    def test_out_markup(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-out="content"/>
            </t>""",
            }
        )
        result = """
                <div><span>toto</span></div>
        """
        rendered = self.env["ir.qweb"]._render(t.id, {})
        self.assertEqual(rendered.strip(), result.strip())

    def test_out_default_value(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="out-default">
                <span rows="10" t-out="a">
                    DEFAULT
                    <t t-out="'Text'" />
                </span>
            </t>""",
            }
        )
        result = """
                <span rows="10">Hello</span>
        """
        rendered = self.env["ir.qweb"]._render(t.id, {"a": "Hello"})
        self.assertEqual(str(rendered.strip()), result.strip())

        result = """
                <span rows="10">
                    DEFAULT
                    Text
                </span>
        """
        rendered = self.env["ir.qweb"]._render(t.id, {})
        self.assertEqual(str(rendered.strip()), result.strip())

    def test_esc_markup(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-esc="content"/>
            </t>""",
            }
        )
        ref = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="esc-markup">
                <t t-set="content"><span>toto</span></t>
                <div t-out="content"/>
            </t>""",
            }
        )
        rendered = self.env["ir.qweb"]._render(t.id, {})
        result = self.env["ir.qweb"]._render(ref.id, {})
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_from_body(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="attr-set">
                <t t-set="abc"> <span a="b"> a </span> </t>
                <div t-if="abc">123</div>
                <div t-if="not abc">456</div>
            </t>""",
            }
        )
        result = """
                <div>123</div>
            """
        rendered = self.env["ir.qweb"]._render(t.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_spaces(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test">
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
            </t>""",
            }
        )
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
        rendered = str(self.env["ir.qweb"]._render(t.id))
        self.assertEqual(rendered.strip(), result.strip())

    def test_if_comment(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test">
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
            </t>""",
            }
        )
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
        rendered = str(self.env["ir.qweb"]._render(t.id))
        self.assertEqual(rendered.strip(), result.strip())

    def test_error_message_1(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test">
                <section>
                    <div t-esc="abc + def">
                        <span>content</span>
                    </div>
                </section>
            </t>""",
            }
        )
        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn('<div t-esc="abc + def"/>', error)

    def test_error_message_2(self):
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name="test">
                <section>
                    <div t-esc="abc + def + (">
                        <span>content</span>
                    </div>
                </section>
            </t>""",
            }
        )
        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("Can not compile expression", error)
            self.assertIn('<div t-esc="abc + def + ("/>', error)

    def test_error_message_3(self):
        template = """<section>
                    <div t-esc="1+2">
                        <span>content</span>
                    </div>
                </section>"""
        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(template)
        try:
            self.env["ir.qweb"]._render(template)
        except QWebError as e:
            self.assertIn(
                "Inline templates must be passed as `etree` documents", str(e)
            )

        template = """toto <t t-esc="content"/>"""
        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(template)
        try:
            self.env["ir.qweb"]._render(template)
        except QWebError as e:
            self.assertIn(
                "Inline templates must be passed as `etree` documents", str(e)
            )

    def test_error_message_4(self):
        with self.assertRaises(MissingError):
            self.env["ir.qweb"]._render(-999)
        try:
            self.env["ir.qweb"]._render(-999)
        except MissingError as e:
            self.assertIn("Template does not exist or has been deleted", str(e))

        with self.assertRaises(MissingError):
            self.env["ir.qweb"]._render("not.wrong_template_xmlid")
        try:
            self.env["ir.qweb"]._render("not.wrong_template_xmlid")
        except MissingError as e:
            self.assertIn("Template not found", str(e))

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(False)
        try:
            self.env["ir.qweb"]._render(False)
        except QWebError as e:
            self.assertIn("template is required", str(e))

    def test_error_message_5(self):
        with self.assertRaises(MissingError, msg="Not Found"):
            self.env["ir.qweb"]._render(-9999)

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_error_message_6(self):
        html = self.env["ir.qweb"]._render(-9999, raise_if_not_found=False)
        self.assertEqual("", html)

        html = self.env["ir.qweb"]._render(-9999, raise_if_not_found=False)
        self.assertEqual("", html)

        with self.assertRaises(MissingError, msg="Not Found"):
            self.env["ir.qweb"]._render(-9999)

    def test_error_message_7(self):
        with self.assertRaises(UserError, msg="Not Found"):
            self.env["ir.qweb"]._render(-9999)

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_error_message_8(self):
        html = self.env["ir.qweb"]._render(-9999, raise_if_not_found=False)
        self.assertEqual("", html)

        html = self.env["ir.qweb"]._render(-9999, raise_if_not_found=False)
        self.assertEqual("", html)

        with self.assertRaises(UserError, msg="Not Found"):
            self.env["ir.qweb"]._render(-9999)

    def test_error_message_9(self):
        skip_if_dev_mode("qweb")
        target = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.test_qweb_error",
                "arch_db": """<t t-name="test">
                <section>
                    <div t-out="abc + def">
                        <span>content</span>
                    </div>
                </section>
            </t>""",
            }
        )
        wrap = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "key": "base.test_qweb_wrap",
                "arch": """<div><t t-call="base.test_qweb_error"/></div>""",
            }
        )
        t = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": """<div><t t-call="base.test_qweb_wrap"/></div>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            self.assertEqual(
                str(e),
                "Error while rendering the template:\n"
                "    TypeError: unsupported operand type(s) for +: 'NoneType' and 'NoneType'\n"
                "    Template: base.test_qweb_error\n"
                f"    Reference: {target.id}\n"
                "    Path: /t/section/div\n"
                '    Element: <div t-out="abc + def"/>\n'
                f"    From: ({t.id}, '/div/t', '<t t-call=\"base.test_qweb_wrap\"/>')\n"
                f"          ({wrap.id}, '/div/t', '<t t-call=\"base.test_qweb_error\"/>')\n"
                f"          ({target.id}, '/t/section/div', '<div t-out=\"abc + def\"/>')",
            )

    def test_error_message_10(self):
        skip_if_dev_mode("qweb")
        a = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.test_qweb_error",
                "arch_db": """<t t-name="test"><section><div t-out="0"/></section></t>""",
            }
        )
        wrap = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "key": "base.test_qweb_wrap",
                "arch": """<div><t t-call="base.test_qweb_error"><span t-out="abc + def"/></t></div>""",
            }
        )
        t = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": """<div><t t-call="base.test_qweb_wrap"/></div>""",
            }
        )

        try:
            self.env["ir.qweb"]._render(t.id)
        except QWebError as e:
            self.assertEqual(
                str(e),
                "Error while rendering the template:\n"
                "    TypeError: unsupported operand type(s) for +: 'NoneType' and 'NoneType'\n"
                "    Template: base.test_qweb_wrap\n"
                f"    Reference: {wrap.id}\n"
                "    Path: /div/t/span\n"
                '    Element: <span t-out="abc + def"/>\n'
                f"    From: ({t.id}, '/div/t', '<t t-call=\"base.test_qweb_wrap\"/>')\n"
                f"          ({wrap.id}, '/div/t', '<t t-call=\"base.test_qweb_error\"/>')\n"
                f"          ({a.id}, '/t/section/div', '<div t-out=\"0\"/>')\n"
                f"          ({wrap.id}, '/div/t', '<t t-call=\"base.test_qweb_error\"/>')\n"
                f"          ({wrap.id}, '/div/t/span', '<span t-out=\"abc + def\"/>')",
            )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id)

    def test_error_message_11(self):
        skip_if_dev_mode("qweb")
        v = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.view_test_error_11_callee",
                "arch_db": '<article><t t-out="b % 99"/></article>',
            }
        )
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.view_test_error_11",
                "arch_db": """<section>
                    <t t-set="a"><div><t t-out="1/div"/> (%s)</div></t>
                    <t t-call="base.view_test_error_11_callee" b="a"/>
                </section>""",
            }
        )

        xml = self.env["ir.qweb"]._render(t.id, {"div": 1})
        self.assertEqual(
            str(xml).strip(),
            """<section><article><div>1.0 (99)</div></article>
                </section>""",
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id, {"div": 0})

        try:
            self.env["ir.qweb"]._render(t.id, {"div": 0})
        except QWebError as e:
            self.assertEqual(
                str(e),
                "Error while rendering the template:\n"
                "    ZeroDivisionError: division by zero\n"
                "    Template: base.view_test_error_11\n"
                f"    Reference: {t.id}\n"
                "    Path: /section/t[1]/div/t\n"
                '    Element: <t t-out="1/div"/>\n'
                f"    From: ({t.id}, '/section/t[2]', '<t t-call=\"base.view_test_error_11_callee\" b=\"a\"/>')\n"
                f"          ({v.id}, '/article/t', '<t t-out=\"b % 99\"/>')\n"
                f"          ({t.id}, '/section/t[1]', '<t t-set=\"a\"/>')\n"
                f"          ({t.id}, '/section/t[1]/div/t', '<t t-out=\"1/div\"/>')",
            )

        self.env.registry.clear_cache("templates")

        try:
            self.env["ir.qweb"]._render(t.id, {"div": 0})
        except QWebError as e:
            self.assertEqual(
                str(e),
                "Error while rendering the template:\n"
                "    ZeroDivisionError: division by zero\n"
                "    Template: base.view_test_error_11\n"
                f"    Reference: {t.id}\n"
                "    Path: /section/t[1]/div/t\n"
                '    Element: <t t-out="1/div"/>\n'
                f"    From: ({t.id}, '/section/t[2]', '<t t-call=\"base.view_test_error_11_callee\" b=\"a\"/>')\n"
                f"          ({v.id}, '/article/t', '<t t-out=\"b % 99\"/>')\n"
                f"          ({t.id}, '/section/t[1]', '<t t-set=\"a\"/>')\n"
                f"          ({t.id}, '/section/t[1]/div/t', '<t t-out=\"1/div\"/>')",
            )

    def test_error_message_12(self):
        self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.view_test_error_9_callee",
                "arch_db": '<article><t t-out="b"/></article>',
            }
        )
        t = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.view_test_error_9",
                "arch_db": """<section>
                    <t t-set="a"><div><t t-out="1/div"/> (%s)</div></t>
                    <t t-call="base.view_test_error_9_callee" b="a"/>
                </section>""",
            }
        )

        xml = self.env["ir.qweb"]._render(t.id, {"div": 1})
        self.assertEqual(
            str(xml).strip(),
            """<section><article><div>1.0 (%s)</div></article>
                </section>""",
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id, {"div": 0})

        try:
            self.env["ir.qweb"]._render(t.id, {"div": 0})
        except QWebError as e:
            error = str(e)
            self.assertIn("ZeroDivisionError", error)
            self.assertIn('Element: <t t-out="1/div"/>', error)
            self.assertIn("""'/section/t[1]', '<t t-set="a"/>'""", error)
            self.assertIn("""'/article/t', '<t t-out="b"/>'""", error)
            self.assertIn(
                """'/section/t[2]', '<t t-call="base.view_test_error_9_callee" b="a"/>'""",
                error,
            )

        self.env.registry.clear_cache("templates")

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(t.id, {"div": 0})

        try:
            self.env["ir.qweb"]._render(t.id, {"div": 0})
        except QWebError as e:
            error = str(e)
            self.assertIn("ZeroDivisionError", error)
            self.assertIn("""'/section/t[1]', '<t t-set="a"/>'""", error)
            self.assertIn("""'/article/t', '<t t-out="b"/>'""", error)
            self.assertIn(
                """'/section/t[2]', '<t t-call="base.view_test_error_9_callee" b="a"/>'""",
                error,
            )

    def test_error_message_13(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<section><t t-set="a" t-value="env.__stuff"/></section>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(view.id)

        try:
            self.env["ir.qweb"]._render(view.id)
        except QWebError as e:
            self.assertEqual(
                str(e),
                "Error while rendering the template:\n"
                "    SyntaxError: Using variable names with '__' is not allowed: '__stuff'\n"
                f"    Template: {view.key}\n"
                f"    Reference: {view.id}\n"
                "    Path: /section/t\n"
                '    Element: <t t-set="a" t-value="env.__stuff"/>\n'
                f"    From: ({view.id}, '/section/t', '<t t-set=\"a\" t-value=\"env.__stuff\"/>')",
            )

    def test_error_message_14(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """
                <section>
                    <t t-set="val"><b>TOTO</b></t>
                    <t t-set="name" t-valuef="irQweb"/>
                    <t t-set="a" t-value="val[name]"/>
                </section>""",
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(view.id)

        try:
            self.env["ir.qweb"]._render(view.id)
        except QWebError as e:
            err = repr(e.__context__)
            self.assertIn("TypeError", err)
            self.assertIn("indices must be integers", err)

    def test_call_set(self):
        view0 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <table>
                        <tr><td t-out="a"/></tr>
                        <t t-set="a">3</t>
                    </table>
                </t>
            """,
            }
        )
        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)VALUES ('dummy', 'ir.ui.view', %s, 'base')",
            [view0.id],
        )

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": """
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
            """,
            }
        )

        result = self.env["ir.qweb"]._render(view1.id, {})
        self.assertEqual(
            etree.fromstring(result),
            etree.fromstring("""
            <div>
                <table>
                    <tr><td>1</td></tr>
                </table>
                <span>1</span>
                <span>1</span>
            </div>
        """),
            "render t-call use lexical scoping, t-call content use independant scoping",
        )

    def test_call_error(self):
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": """
                <t t-name="base.other">
                    <div>
                        <t t-call="base.dummy"/>
                    </div>
                </t>
            """,
            }
        )

        with self.assertRaises(MissingError):
            self.env["ir.qweb"]._render(view1.id)

        try:
            self.env["ir.qweb"]._render(view1.id)
        except MissingError as e:
            error = str(e.qweb)
            self.assertIn("Template not found: 'base.dummy'", error)
            self.assertIn('<t t-call="base.dummy"/>', error)

    def test_call_infinite_recursion(self):
        self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "key": "base.dummy",
                "arch_db": '<article><t t-call="base.dummy"/></article>',
            }
        )
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": '<div><t t-call="base.dummy"/></div>',
            }
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(view1.id)

        try:
            self.env["ir.qweb"]._render(view1.id)
        except QWebError as e:
            error = str(e)
            self.assertIn("Qweb template infinite recursion", error)
            self.assertIn("""'/article/t', '<t t-call="base.dummy"/>'""", error)

    def test_call_call_0(self):
        self.env["ir.ui.view"].create(
            {
                "name": "micro_child",
                "type": "qweb",
                "key": "base.micro_child",
                "arch_db": '<article><t t-out="0"/></article>',
            }
        )
        self.env["ir.ui.view"].create(
            {
                "name": "wrap",
                "type": "qweb",
                "key": "base.wrap",
                "arch_db": '<wrap><t t-out="0"/></wrap>',
            }
        )
        self.env["ir.ui.view"].create(
            {
                "name": "child",
                "type": "qweb",
                "key": "base.child",
                "arch_db": '<t t-call="base.wrap"><section><t t-call="base.micro_child"><t t-out="0"/></t></section></t>',
            }
        )
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": '<div><t t-call="base.child">test</t></div>',
            }
        )

        result = self.env["ir.qweb"]._render(view1.id)
        self.assertEqual(
            str(result),
            "<div><wrap><section><article>test</article></section></wrap></div>",
        )

    def test_call_foreach_call(self):
        self.env["ir.ui.view"].create(
            {
                "name": "child",
                "type": "qweb",
                "key": "base.child",
                "arch_db": '<article><t t-out="toto"/></article>',
            }
        )
        self.env["ir.ui.view"].create(
            {
                "name": "wrap",
                "type": "qweb",
                "key": "base.wrap",
                "arch_db": '<wrap><t t-out="0"/></wrap>',
            }
        )
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "other",
                "type": "qweb",
                "arch": '<t t-call="base.wrap"><div><t t-foreach="[1,2,3]" t-as="toto"><t t-call="base.child">test</t></t></div></t>',
            }
        )

        result = self.env["ir.qweb"]._render(view1.id)
        self.assertEqual(
            str(result),
            "<wrap><div><article>1</article><article>2</article><article>3</article></div></wrap>",
        )

    def test_render_t_call_propagates_t_lang(self):
        current_lang = "en_US"
        other_lang = "fr_FR"

        lang = self.env["res.lang"]._activate_lang(other_lang)
        lang.write({"decimal_point": "*", "thousands_sep": "/"})

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "callee",
                "type": "qweb",
                "arch": """
                <t t-name="base.callee">
                    <t t-esc="9000000.00" t-options="{'widget': 'float', 'precision': 2}" />
                </t>
            """,
            }
        )
        self.env["ir.model.data"].create(
            {
                "name": "callee",
                "model": "ir.ui.view",
                "module": "base",
                "res_id": view1.id,
            }
        )

        view2 = self.env["ir.ui.view"].create(
            {
                "name": "calling",
                "type": "qweb",
                "arch": """
                <t t-name="base.calling">
                    <t t-call="base.callee" t-lang="'%s'" />
                </t>
            """
                % other_lang,
            }
        )

        rendered = (
            self.env["ir.qweb"]
            .with_context(lang=current_lang)
            ._render(view2.id)
            .strip()
        )
        self.assertEqual(rendered, "9/000/000*00")

    def test_render_barcode(self):
        partner = self.env["res.partner"].create(
            {"name": "bacode_test", "barcode": "test"}
        )

        view = self.env["ir.ui.view"].create(
            {
                "name": "a_barcode_view",
                "type": "qweb",
            }
        )

        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'width': 100, 'height': 30}"/>"""
        rendered = (
            self.env["ir.qweb"]._render(view.id, values={"partner": partner}).strip()
        )
        self.assertRegex(
            rendered,
            r'<div><img alt="Barcode test" src="data:image/png;base64,\S+"></div>',
        )

        partner.barcode = "4012345678901"
        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'symbology': 'EAN13', 'width': 100, 'height': 30, 'img_style': 'width:100%;', 'img_alt': 'Barcode'}"/>"""
        ean_rendered = (
            self.env["ir.qweb"]._render(view.id, values={"partner": partner}).strip()
        )
        self.assertRegex(
            ean_rendered,
            r'<div><img style="width:100%;" alt="Barcode" src="data:image/png;base64,\S+"></div>',
        )

        view.arch = """<div t-field="partner.barcode" t-options="{'widget': 'barcode', 'symbology': 'auto', 'width': 100, 'height': 30, 'img_style': 'width:100%;', 'img_alt': 'Barcode'}"/>"""
        auto_rendered = (
            self.env["ir.qweb"]._render(view.id, values={"partner": partner}).strip()
        )
        self.assertRegex(
            auto_rendered,
            r'<div><img style="width:100%;" alt="Barcode" src="data:image/png;base64,\S+"></div>',
        )

    def test_render_comment_tail(self):

        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
            <t>
                <!-- it is a comment -->
                <!-- it is another comment -->
                Text 1
                <!-- it is still another comment -->
                Text 2
                <t>ok</t>
            </t>
            """,
            }
        )
        emptyline = "\n                "
        expected = markupsafe.Markup(
            "Text 1" + emptyline + emptyline + "Text 2" + emptyline + "ok"
        )
        self.assertEqual(self.env["ir.qweb"]._render(view1.id).strip(), expected)

    def test_render_comments(self):
        comment = "<!-- Hello, world! -->"
        view = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": f"<t><p>{comment}</p></t>",
            }
        )
        QWeb = self.env["ir.qweb"]
        self.assertEqual(
            QWeb.with_context(preserve_comments=False)._render(view.id),
            markupsafe.Markup("<p></p>"),
            "Should not have the comment",
        )
        self.assertEqual(
            QWeb.with_context(preserve_comments=True)._render(view.id),
            markupsafe.Markup(f"<p>{comment}</p>"),
            "Should have the comment",
        )

    def test_render_processing_instructions(self):
        p_instruction = "<?hello world?>"
        view = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": f"<t><p>{p_instruction}</p></t>",
            }
        )
        QWeb = self.env["ir.qweb"]
        self.assertEqual(
            QWeb.with_context(preserve_comments=False)._render(view.id),
            markupsafe.Markup("<p></p>"),
            "Should not have the processing instruction",
        )
        self.assertEqual(
            QWeb.with_context(preserve_comments=True)._render(view.id),
            markupsafe.Markup(f"<p>{p_instruction}</p>"),
            "Should have the processing instruction",
        )

    def test_render_widget_contact(self):
        u = self.env["res.users"].create(
            {
                "name": "Test",
                "login": "test@example.com",
            }
        )
        u.name = ""
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy"><root><span t-esc="user" t-options='{"widget": "contact", "fields": ["name"]}' /></root></t>
            """,
            }
        )
        self.env["ir.qweb"]._render(view1.id, {"user": u})

    def test_render_widget_duration_fallback(self):
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "=", "pt_BR")]
        ).active = True
        view1 = self.env["ir.ui.view"].create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy"><root><span t-esc="3600" t-options='{"widget": "duration", "format": "short"}' /></root></t>
            """,
            }
        )
        self.env["ir.qweb"].with_context(lang="pt_BR")._render(view1.id, {})

    def test_render_template_from_file(self):
        with file_open("base/tests/file_template/file_expected_render.xml") as f:
            expected_result = etree.fromstring(f.read())
        rendered_result = self.env["ir.qweb"]._render(
            "base/tests/file_template/templates/file_template.xml",
            values={
                "document_name": "Test Document",
                "partner": {
                    "name": "Jerry",
                    "forename": "Khan",
                },
            },
        )
        self.assertEqual(etree.fromstring(rendered_result), expected_result)

    def test_render_template_from_file_special_cases(self):
        self.env["ir.qweb"]._render(
            "base/tests/file_template/templates/../templates/file_template.xml",
            values={
                "document_name": "Test Document",
                "partner": {
                    "name": "Jerry",
                    "forename": "Khan",
                },
            },
        )

        self.env["ir.qweb"]._render(
            "./base/tests//file_template/templates/file_template.xml",
            values={
                "document_name": "Test Document",
                "partner": {
                    "name": "Jerry",
                    "forename": "Khan",
                },
            },
        )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(
                "base/tests/file_template/templates/../unreadable_file_template.xml",
                values={},
            )

        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render(
                "base/tests/file_template/unreadable_file_template.xml",
                values={},
            )

    def test_render_template_from_file_compile_cached(self):
        skip_if_dev_mode("xml")
        qweb = self.env["ir.qweb"]
        path = "base/tests/file_template/templates/file_template.xml"
        first = qweb._compile(path)
        second = qweb._compile(path)
        self.assertIs(
            first[0],
            second[0],
            "file template compilation must be served from the ormcache",
        )
        values = {
            "document_name": "Test Document",
            "partner": {"name": "Jerry", "forename": "Khan"},
        }
        self.assertEqual(qweb._render(path, values), qweb._render(path, values))

    def test_render_template_from_file_unknown_module(self):
        qweb = self.env["ir.qweb"]
        with self.assertRaises(ValueError) as cm:
            qweb._generate_code_file_cached("unknown_module_xyz/templates/foo.xml")
        self.assertIn("unknown_module_xyz", str(cm.exception))
        self.assertIn("not a known Odoo module", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            qweb._generate_code_file_cached(
                "base/tests/file_template/unreadable_file_template.xml"
            )
        self.assertIn("unreadable_file_template.xml", str(cm.exception))
        self.assertNotIn("%s", str(cm.exception))

    def test_t_out_options_without_widget(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "options-no-widget",
                "type": "qweb",
                "arch_db": """<t t-name="options-no-widget">
                    <span t-out="5" t-options-format="'x'"/>
                </t>""",
            }
        )
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(view.id, {})
        self.assertIsInstance(cm.exception.__cause__, ValueError)
        self.assertIn("'widget' option", str(cm.exception.__cause__))

    def test_static_node_scheme_not_scrubbed(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "static-scheme",
                "type": "qweb",
                "arch_db": """<t t-name="static-scheme">
                    <a href="javascript:alert(2)">static</a>
                    <a t-att-href="url">dynamic</a>
                </t>""",
            }
        )
        rendered = str(
            self.env["ir.qweb"]._render(view.id, {"url": "javascript:alert(1)"})
        )
        self.assertIn('href="javascript:alert(2)"', rendered)
        self.assertNotIn("javascript:alert(1)", rendered)
        self.assertNotIn("__is_static_node", rendered)

    def test_void_element(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "master",
                "type": "qweb",
                "arch_db": """<t t-name='master'>
                <meta name="1"/>
                <t t-set="data" t-value="1"/>
                <meta groups="base.group_no_one" name="2"/>
                <meta t-if="False" name="3"/>
                <meta t-if="True" name="4"/>
                <span t-out="1"/>
            </t>""",
            }
        )

        result = """
                <meta name="1"/>
                <meta name="4"/>
                <span>1</span>
            """
        rendered = self.env["ir.qweb"]._render(view.id)

        self.assertEqual(str(rendered).strip(), result.strip())

    def test_space_remove_technical_space_t_foreach(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "master",
                "type": "qweb",
                "arch_db": """<t t-name='master'>
                    <section>
                        <article t-foreach="[0, 1, 2]" t-as="value" t-esc="value"/>
                        <t t-foreach="[0, 1, 2]" t-as="value">
                            <article t-esc="value"/>
                        </t>
                    </section>
                </t>""",
            }
        )

        result = """
                    <section>
                        <article>0</article><article>1</article><article>2</article>
                            <article>0</article>
                            <article>1</article>
                            <article>2</article>
                    </section>"""

        rendered = self.env["ir.qweb"]._render(view.id)

        self.assertEqual(str(rendered), result)

    def test_t_foreach_t_call(self):
        self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.test",
                "arch_db": """<t t-out="value"/>""",
            }
        )
        view = self.env["ir.ui.view"].create(
            {
                "name": "master",
                "type": "qweb",
                "arch_db": """<t t-name='master'>
                    <t t-set="value" t-value="3"/>
                    a) <t t-call="base.test"/>
                    b) <t t-foreach="[0, 1]" t-as="value"><t t-call="base.test"/>;</t>
                    c) <t t-foreach="[0, 1]" t-as="value" t-call="base.test"/>
                </t>""",
            }
        )

        result = """
                    a) 3
                    b) 0;1;
                    c) 01
        """
        rendered = self.env["ir.qweb"]._render(view.id)
        self.assertEqual(str(rendered).strip(), result.strip())

    def test_space_remove_technical_all(self):
        test = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "arch_db": """<t t-name='test'>
                <span t-out="value"/>
            </t>""",
            }
        )
        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)VALUES ('test', 'ir.ui.view', %s, 'base')",
            [test.id],
        )

        view = self.env["ir.ui.view"].create(
            {
                "name": "master",
                "type": "qweb",
                "arch_db": """<t t-name='master'>

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
                </t>""",
            }
        )

        result = """
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
                    </section>"""

        rendered = self.env["ir.qweb"]._render(view.id)
        self.assertEqual(str(rendered), result)


@tagged("post_install", "-at_install")
class TestQwebPerformance(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo.group_ids = cls.env.ref("base.group_user")

    def test_render_queries(self):
        IrUiView = self.env["ir.ui.view"]
        header_0 = IrUiView.create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.testing_header_0",
                "arch_db": """<span>0</span>""",
            }
        )
        IrUiView.create(
            [
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_header_1",
                    "arch_db": """<span>1</span>""",
                },
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_header",
                    "arch_db": f"""<t t-name="base.testing_header">
                <t t-call="{header_0.id}"/>
                <header>header</header>
                <t t-call="base.testing_header_1"/>
            </t>""",
                },
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_footer_0",
                    "arch_db": """<span>0</span>""",
                },
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_footer_1",
                    "arch_db": """<span>1</span>""",
                },
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_footer",
                    "arch_db": """<t t-name="base.testing_footer">
                <t t-call="base.testing_footer_0"/>
                <header>header</header>
                <t t-call="base.testing_footer_1"/>
            </t>""",
                },
                {
                    "name": "test",
                    "type": "qweb",
                    "key": "base.testing_layout",
                    "arch_db": """<t t-name="base.testing_layout">
                <section>
                    <header><t t-call="base.testing_header"/></header>
                    <article><t t-out="0"/></article>
                    <header><t t-call="base.testing_footer"/></header>
                </section>
            </t>""",
                },
            ]
        )
        view = IrUiView.create(
            {
                "name": "test",
                "type": "qweb",
                "key": "base.testing_content",
                "arch_db": """<t t-call="base.testing_layout"><div><t t-call="base.testing_header_0"/><t t-out="doc.name"/></div></t>""",
            }
        )
        doc = self.env["ir.attachment"].create(
            {
                "name": "test",
                "type": "url",
                "public": True,
            }
        )

        expected = """
                <section>
                    <header><span>0</span>
                <header>header</header><span>1</span></header>
                    <article><div><span>0</span>%s</div></article>
                    <header><span>0</span>
                <header>header</header><span>1</span></header>
                </section>"""

        env = self.env(user=self.user_demo)

        env["ir.qweb"]._render("base.testing_content", {"doc": doc})

        doc.with_env(env).fetch(["name"])
        env.user.fetch(["name"])

        def check(template, name, queries):
            doc.name = name
            init = env.cr.sql_statement_count
            value = env["ir.qweb"]._render(template, {"doc": doc})
            self.assertEqual(str(value), expected % name)
            self.assertEqual(
                env.cr.sql_statement_count - init,
                queries,
                f"Maximum queries: {queries}",
            )

        FIRST_SEARCH_FETCH = 1
        OTHER_SEARCH_FETCH = 3
        ARCH_COMBINE = 4

        self.env.registry.clear_cache("templates")
        view.invalidate_model()

        check(
            "base.testing_content",
            "test-cold-0",
            FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE,
        )
        check("base.testing_content", "test-hot-0", 0)
        check("base.testing_content", "test-hot-1", 0)

        view.invalidate_model()
        check("base.testing_content", "test-hot-2", 0)
        check(view.id, "test-hot-id", 0)

        self.env.registry.clear_cache("templates")
        check(
            view.id,
            "test-cold-id-1",
            FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE,
        )

        self.env.registry.clear_cache("templates")
        view.invalidate_model()
        check(
            view.id,
            "test-cold-id-2",
            FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE,
        )

        self.env.registry.clear_cache("templates")
        check(
            "base.testing_content",
            "test-cold-1",
            FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE,
        )

        self.env.registry.clear_cache("templates")
        check(
            view.id,
            "test-cold-id-3",
            FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE - 1,
        )


@tagged("post_install", "-at_install")
class TestQWebCompileIsolation(TransactionCase):
    @staticmethod
    def _directive_attrs(element):
        return [
            attr
            for node in element.iter()
            if isinstance(node.tag, str)
            for attr in node.attrib
            if attr.startswith("t-") or attr == "groups"
        ]

    def test_compile_is_idempotent(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "compile_isolation_idem",
                "type": "qweb",
                "key": "base.compile_isolation_idem",
                "arch": """<t t-name="base.compile_isolation_idem">
                    <div t-att-class="'c'" t-foreach="[1, 2, 3]" t-as="i"><span t-esc="i"/></div>
                </t>""",
            }
        )
        qweb = self.env["ir.qweb"]
        code1 = qweb._generate_code(view.id)[0]
        code2 = qweb._generate_code(view.id)[0]
        self.assertEqual(
            code1,
            code2,
            "recompiling the same template is not idempotent — the first compile "
            "mutated the shared source tree",
        )

    def test_render_does_not_mutate_cached_tree(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "compile_isolation_cache",
                "type": "qweb",
                "key": "base.compile_isolation_cache",
                "arch": """<t t-name="base.compile_isolation_cache">
                    <div t-foreach="[1, 2, 3]" t-as="i"><span t-esc="i"/></div>
                </t>""",
            }
        )
        qweb = self.env["ir.qweb"]
        before = self._directive_attrs(qweb._get_template(view.id)[0])
        self.assertTrue(before, "sanity: the template must carry t-* directives")

        rendered = str(qweb._render(view.id))
        self.assertIn("<span>1</span>", rendered)
        self.assertIn("<span>3</span>", rendered)

        after = self._directive_attrs(qweb._get_template(view.id)[0])
        self.assertEqual(
            before,
            after,
            "rendering stripped the transaction-cached source tree; a recompile "
            "after a templates-cache eviction would render corrupted output",
        )

    def test_render_reused_etree_is_stable(self):
        qweb = self.env["ir.qweb"]
        element = etree.fromstring('<t><span t-esc="1 + 1"/></t>')
        first = str(qweb._render(element))
        second = str(qweb._render(element))
        self.assertEqual(first, "<span>2</span>")
        self.assertEqual(
            first,
            second,
            "re-rendering a reused etree produced different output — the caller's "
            "element was mutated during compilation",
        )


class TestQWebHelpers(TransactionCase):
    @staticmethod
    def _context(**fields):
        defaults = {
            "context": {},
            "ref": None,
            "ref_name": None,
            "ref_xml": None,
            "template": None,
            "root": None,
            "make_name": None,
            "template_functions": {},
            "text_concat": [],
            "nsmap": {},
        }
        return CompileContext(**{**defaults, **fields})

    def test_compiler_state_and_caller_context_are_separate_namespaces(self):
        compile_context = self._context(
            context={"ref_name": "the caller's", "snippet-key": "abc"},
            ref_name="the compiler's",
        )
        self.assertEqual(compile_context.ref_name, "the compiler's")
        self.assertEqual(compile_context.get("ref_name"), "the caller's")
        self.assertEqual(compile_context.get("snippet-key"), "abc")
        self.assertIn("snippet-key", compile_context)
        self.assertNotIn("ref", compile_context)

    def test_compile_context_is_not_subscriptable(self):
        compile_context = self._context(context={"snippet-key": "abc"})
        msg = (
            "subscripting is what made the two namespaces indistinguishable; "
            "its absence is the compile context's design, not an omission"
        )
        with self.assertRaises(TypeError, msg=msg):
            compile_context["ref_name"]
        with self.assertRaises(TypeError, msg=msg):
            compile_context["snippet-key"]

    def test_compile_context_refuses_an_undeclared_field(self):
        compile_context = self._context()
        with self.assertRaises(AttributeError):
            compile_context.ref_nmae = "typo"

    def test_compile_format(self):
        qweb = self.env["ir.qweb"]
        code = qweb._compile_format("Save 50%")
        self.assertEqual(unsafe_eval(code, {"self": qweb}, {"values": {}}), "Save 50%")
        code = qweb._compile_format("Hi #{name} 50%")
        self.assertEqual(
            unsafe_eval(code, {"self": qweb}, {"values": {"name": "Bob"}}),
            "Hi Bob 50%",
        )
        code = qweb._compile_format("100% #{x}%")
        self.assertEqual(
            unsafe_eval(code, {"self": qweb}, {"values": {"x": 7}}), "100% 7%"
        )

    def test_qweb_call_parameters_repr_root_frame(self):
        params = QwebCallParameters(
            context={},
            view_ref=42,
            method=None,
            values=None,
            scope=False,
            directive="render",
            path_xml=None,
        )
        self.assertIn("view_ref=42", repr(params))

    def test_qweb_json_default(self):
        class Unserializable:
            pass

        content = QwebContent(self.env["ir.qweb"], None)
        content.html = "<b>x</b>"
        self.assertEqual(qweb_json.dumps({"c": content}), '{"c": "<b>x</b>"}')
        with self.assertRaisesRegex(TypeError, "Unserializable is not JSON"):
            qweb_json.dumps({"u": Unserializable()})
        self.assertEqual(
            qweb_json.dumps({"u": Unserializable()}, default=lambda o: "D"),
            '{"u": "D"}',
        )

    def test_format_attributes(self):
        self.assertEqual(
            format_attributes(
                {"a": 1, "b": "", "c": None, "d": 0, "e": False, 'x"y': "<&>"}
            ),
            ' a="1" b="" x&#34;y="&lt;&amp;&gt;"',
        )

    def test_is_static_node(self):
        qweb = self.env["ir.qweb"]
        ctx = self._context(nsmap={})
        self.assertTrue(qweb._is_static_node(etree.fromstring('<div class="x"/>'), ctx))
        self.assertTrue(
            qweb._is_static_node(etree.fromstring('<div t-tag-open="div"/>'), ctx)
        )
        self.assertFalse(qweb._is_static_node(etree.fromstring("<t/>"), ctx))
        self.assertFalse(
            qweb._is_static_node(etree.fromstring('<div t-att-x="1"/>'), ctx)
        )
        self.assertFalse(
            qweb._is_static_node(
                etree.fromstring('<div groups="base.group_user"/>'), ctx
            )
        )

    def test_render_asset_nodes(self):
        qweb = self.env["ir.qweb"]
        cached = {"src": "/web/x.js", "type": "module", "text": "import 'a';"}
        nodes = [
            ("link", {"rel": "stylesheet", "href": "/web/a.css", "media": None}),
            ("script", cached),
            ("script", {"src": "/web/y.js", "async": True, "defer": False}),
        ]
        self.assertEqual(
            "".join(qweb._render_asset_nodes(nodes)),
            '<link rel="stylesheet" href="/web/a.css"/>\n        '
            '<script src="/web/x.js" type="module">import \'a\';</script>\n        '
            '<script src="/web/y.js" async="True"></script>',
        )
        self.assertIn("text", cached, "the cached node dict must not be mutated")
        self.assertEqual(
            "".join(qweb._render_asset_nodes([("script", {"text": "<&>"})])),
            "<script><&></script>",
            "inline text is emitted as is, attributes are escaped",
        )
        self.assertEqual("".join(qweb._render_asset_nodes([("meta", None)])), "<meta/>")

    def test_namespace_helpers(self):
        qweb = self.env["ir.qweb"]
        el = etree.fromstring('<div xmlns:x="urn:x"/>')
        self.assertEqual(
            qweb._new_namespaces(el, self._context(nsmap={})), [("x", "urn:x")]
        )
        self.assertEqual(
            qweb._new_namespaces(el, self._context(nsmap={"x": "urn:x"})), []
        )
        eld = etree.fromstring('<div xmlns="urn:d"/>')
        self.assertEqual(
            qweb._new_namespaces(eld, self._context(nsmap={})), [(None, "urn:d")]
        )
        self.assertEqual(
            qweb._get_ns_prefix_map(el, self._context(nsmap={})), {"urn:x": "x"}
        )

    def test_compile_out_target(self):
        qweb = self.env["ir.qweb"]
        for attr, expr, expected in (
            ("t-out", "foo", ("t-out", "foo")),
            ("t-field", "rec.name", ("t-field", "rec.name")),
            ("t-esc", "foo", ("t-esc", "foo")),
            ("t-raw", "foo", ("t-raw", "foo")),
        ):
            el = etree.fromstring(f'<span {attr}="{expr}"/>')
            self.assertEqual(qweb._compile_out_target(el), expected)
            self.assertNotIn(attr, el.attrib)

    def test_element_marker_roundtrip(self):
        qweb = self.env["ir.qweb"]
        for path, xml in (
            ("/t/div", '<div class="x"/>'),
            ("/t/div/span", '<span t-att-title="a , b" t-out="x + y"/>'),
        ):
            marker = qweb._get_element_marker(path, xml)
            match = ELEMENT_MARKER_REGEXP.match(marker)
            self.assertIsNotNone(match)
            self.assertEqual(ast.literal_eval(match[1]), (path, xml))

    def test_post_processing_att_all_url_attrs(self):
        qweb = self.env["ir.qweb"]
        for attr in ("href", "src", "action", "formaction"):
            self.assertEqual(
                qweb._post_processing_att("a", {attr: "javascript:alert(1)"})[attr],
                "",
                f"{attr} malicious scheme not scrubbed",
            )
            self.assertEqual(
                qweb._post_processing_att("a", {attr: "https://ok/"})[attr],
                "https://ok/",
                f"{attr} safe url wrongly scrubbed",
            )
        self.assertEqual(
            qweb._post_processing_att("a", {"src": "java\tscript:alert(1)"})["src"], ""
        )
        self.assertEqual(
            qweb._post_processing_att("a", {"href": "javascript:history.back()"})[
                "href"
            ],
            "javascript:history.back()",
        )
        self.assertEqual(
            qweb._post_processing_att(
                "a", {"href": "javascript:alert(1)"}, is_static=True
            )["href"],
            "javascript:alert(1)",
        )

    def test_generated_code_contracts(self):
        View = self.env["ir.ui.view"]
        qweb = self.env["ir.qweb"]

        slot = View.create(
            {"name": "s", "type": "qweb", "arch_db": '<t t-name="s"><t t-out="0"/></t>'}
        )
        self.assertIn("values.get('0', '')", qweb._generate_code(slot.id)[0])

        loop = View.create(
            {
                "name": "l",
                "type": "qweb",
                "arch_db": '<t t-name="l"><span t-foreach="s" t-as="i" t-out="i"/></t>',
            }
        )
        self.assertIn("values['i_last'] = False", qweb._generate_code(loop.id)[0])

    def test_error_surrounding(self):
        qweb = self.env["ir.qweb"]
        code_lines = [f"line{n}" for n in range(1, 11)]
        out = qweb._get_error_surrounding_code(code_lines, 5, None)
        self.assertIn("Line triggering the error", out)
        self.assertIn("line5", out)
        self.assertIn("line4", out)
        self.assertIn("line6", out)


class TestQWebRenderStandalone(TransactionCase):
    @staticmethod
    def _load(templates):
        def load(ref):
            return (etree.fromstring(templates[ref]), ref)

        return load

    def test_render_standalone_static(self):
        out = render("m", {}, self._load({"m": "<div><span>hi</span></div>"}))
        self.assertEqual(str(out), "<div><span>hi</span></div>")

    def test_render_standalone_directives(self):
        templates = {
            "m": '<t><span t-out="val"/><b t-if="flag">Y</b><i t-att-data-x="n"/></t>'
        }
        out = render("m", {"val": "hi", "flag": True, "n": 5}, self._load(templates))
        self.assertEqual(str(out), '<span>hi</span><b>Y</b><i data-x="5"></i>')

    def test_render_standalone_body_with_only_assignments(self):
        templates = {
            "m": '<t><t t-set="s"><t t-set="q" t-value="1"/></t>[<t t-out="s"/>]'
            '<t t-call="c"><t t-set="v" t-value="7"/></t></t>',
            "c": '<t t-out="v"/>',
        }
        self.assertEqual(str(render("m", {}, self._load(templates))), "[]7")

    def test_render_standalone_t_set_body_renders_inside_a_server_thread(self):
        # The thread carries the test database's name and the standalone
        # cursor carries none; a QwebContent must still render here.
        templates = {"m": '<t><t t-set="s">S</t>[<t t-out="s"/>]</t>'}
        self.assertTrue(getattr(threading.current_thread(), "dbname", None))
        self.assertEqual(str(render("m", {}, self._load(templates))), "[S]")

    def test_generated_module_has_no_empty_yield_unless_needed(self):
        templates = {"m": '<t><t t-set="s"><b>x</b></t><i t-out="s"/></t>'}
        qweb = _StandaloneQweb(_StandaloneEnv(), (), ())
        code = qweb._generate_code(etree.fromstring(templates["m"]))[0]
        self.assertNotIn("yield ''", code)

    def test_render_standalone_foreach(self):
        templates = {"m": '<t><span t-foreach="items" t-as="i" t-out="i"/></t>'}
        out = render("m", {"items": [1, 2, 3]}, self._load(templates))
        self.assertEqual(str(out), "<span>1</span><span>2</span><span>3</span>")

    @staticmethod
    def _highlighted_line(surrounding):
        lines = (surrounding or "").splitlines()
        for i, line in enumerate(lines):
            if "Line triggering the error" in line:
                return lines[i + 1]
        return None

    def test_error_path_with_delimiter_in_failing_node_attrs(self):
        templates = {"m": '<t><div><span t-att-title="a , b" t-out="x + y"/></div></t>'}
        with self.assertRaises(QWebError) as cm:
            str(render("m", {}, self._load(templates)))
        qweb = cm.exception.qweb
        self.assertEqual(qweb.path, "/t/div/span")
        self.assertTrue(
            qweb.element.startswith("<span"),
            f"element corrupted: {qweb.element!r}",
        )
        self.assertIn('t-out="x + y"', qweb.element)

    def test_error_surrounding_points_at_failing_line_out(self):
        templates = {"m": '<t><div><span t-out="x + y"/></div></t>'}
        with self.assertRaises(QWebError) as cm:
            str(render("m", {}, self._load(templates), dev_mode=True))
        highlighted = self._highlighted_line(cm.exception.qweb.surrounding)
        self.assertIsNotNone(highlighted)
        self.assertIn("content =", highlighted)
        self.assertNotIn("if content is not None", highlighted)

    def test_error_surrounding_points_at_failing_line_if(self):
        templates = {"m": '<t><div><span t-if="x + y">z</span></div></t>'}
        with self.assertRaises(QWebError) as cm:
            str(render("m", {}, self._load(templates), dev_mode=True))
        highlighted = self._highlighted_line(cm.exception.qweb.surrounding)
        self.assertIsNotNone(highlighted)
        self.assertRegex(highlighted.strip(), r"^if \(")


class TestQWebPreloadTrees(TransactionCase):
    def test_tcall_same_target_by_id_and_xmlid(self):
        callee = self.env["ir.ui.view"].create(
            {
                "name": "preload_dedup_callee",
                "type": "qweb",
                "key": "base.preload_dedup_callee",
                "arch": """<t t-name="base.preload_dedup_callee">
                    <span>callee content</span>
                </t>""",
            }
        )
        caller = self.env["ir.ui.view"].create(
            {
                "name": "preload_dedup_caller",
                "type": "qweb",
                "key": "base.preload_dedup_caller",
                "arch": f"""<t t-name="base.preload_dedup_caller">
                    <div>
                        <t t-call="base.preload_dedup_callee"/>
                        <t t-call="{callee.id}"/>
                    </div>
                </t>""",
            }
        )
        rendered = str(self.env["ir.qweb"]._render(caller.id))
        self.assertEqual(
            rendered.count("<span>callee content</span>"),
            2,
            "the same view t-called by id and by xmlid must render both times",
        )

    def test_preload_same_view_both_spellings_direct(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "preload_dedup_direct",
                "type": "qweb",
                "key": "base.preload_dedup_direct",
                "arch": """<t t-name="base.preload_dedup_direct">
                    <span>direct</span>
                </t>""",
            }
        )
        batch = self.env["ir.qweb"]._preload_trees(
            [view.id, "base.preload_dedup_direct"]
        )
        for ref in (view.id, "base.preload_dedup_direct"):
            self.assertIn("template", batch[ref], f"missing tree for ref {ref!r}")
            self.assertIn("<span>direct</span>", batch[ref]["template"])


class TestQWebProfilingWrap(TransactionCase):
    def test_profile_wrap_does_not_mutate_cached_functions(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "profile_wrap",
                "type": "qweb",
                "key": "base.profile_wrap",
                "arch": """<t t-name="base.profile_wrap"><span t-esc="1 + 1"/></t>""",
            }
        )
        qweb = self.env["ir.qweb"].with_context(profile=True)

        functions1, def_name, options = qweb._compile(view.id)
        self.assertTrue(options.get("profile"), "sanity: profile mode expected")
        self.assertEqual(functions1[def_name].__name__, "profiled_method_compile")

        cached_functions = qweb._generate_code_cached(view.id)[0]
        self.assertNotEqual(
            cached_functions[def_name].__name__,
            "profiled_method_compile",
            "profiling wrappers leaked into the cached function mapping",
        )

        functions2 = qweb._compile(view.id)[0]
        self.assertEqual(functions2[def_name].__name__, "profiled_method_compile")
        self.assertIsNot(functions2[def_name], functions1[def_name])


class TestQWebImageDataUri(TransactionCase):
    WEBP_B64 = "UklGRsCpAQBXRUJQVlA4WAoAAAAQAAAAGAQA/wMAQUxQSMywAAAdNANp22T779/0RUREkvqLOTPesG1T21jatpLTSbpXQzTMEw3zWMM81jCPnWG2fTM7vpndvpkd38y2758Y+6a/Ld/Mt3zzT/XwzCKlV0Ooo61UpZIsKLjKc98R"
    PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII="

    def _create_converted_pair(self):
        Attachment = self.env["ir.attachment"]
        origin = Attachment.create(
            {"name": "origin.webp", "raw": base64.b64decode(self.WEBP_B64)}
        )
        converted = Attachment.create(
            {
                "name": "webpcopy.jpg",
                "res_model": "ir.attachment",
                "res_id": origin.id,
                "datas": self.PNG_B64,
            }
        )
        self.assertEqual(converted.mimetype, "image/jpeg", "sanity")
        return converted

    def test_webp_conversion_bytes_source(self):
        converted = self._create_converted_pair()
        qweb = self.env["ir.qweb"].with_context(webp_as_jpg=True)
        uri = qweb._get_converted_image_data_uri(self.WEBP_B64.encode())
        self.assertEqual(uri, f"data:image/png;base64,{converted.datas.decode()}")

    def test_webp_conversion_str_source(self):
        converted = self._create_converted_pair()
        qweb = self.env["ir.qweb"].with_context(webp_as_jpg=True)
        uri = qweb._get_converted_image_data_uri(self.WEBP_B64)
        self.assertEqual(uri, f"data:image/png;base64,{converted.datas.decode()}")

    def test_webp_conversion_memoized_per_transaction(self):
        converted = self._create_converted_pair()
        qweb = self.env["ir.qweb"].with_context(webp_as_jpg=True)
        uri = qweb._get_converted_image_data_uri(self.WEBP_B64)
        self.assertEqual(uri, f"data:image/png;base64,{converted.datas.decode()}")
        with self.assertQueryCount(0):
            self.assertEqual(qweb._get_converted_image_data_uri(self.WEBP_B64), uri)


class TestQWebCompileCacheKeys(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": f"base.{key}", "arch_db": arch}
        )

    def test_preserve_comments_is_part_of_the_cache_key(self):
        view = self._view("pc_key", "<t><p><!-- C --><t t-out='1'/></p></t>")
        qweb = self.env["ir.qweb"]
        for first, second in ((False, True), (True, False)):
            self.env.registry.clear_cache("templates")
            self.assertEqual(
                str(qweb.with_context(preserve_comments=first)._render(view.id)),
                "<p><!-- C -->1</p>" if first else "<p>1</p>",
            )
            self.assertEqual(
                str(qweb.with_context(preserve_comments=second)._render(view.id)),
                "<p><!-- C -->1</p>" if second else "<p>1</p>",
                f"compiled with preserve_comments={first}, reused for {second}",
            )

    def test_caller_nsmap_is_part_of_the_cache_key(self):
        self._view("ns_leaf", "<t><h:td xmlns:h='http://ex/t' t-out=\"'V'\"/></t>")
        self._view(
            "ns_inside",
            "<t><h:table xmlns:h='http://ex/t'><t t-call='base.ns_leaf'/></h:table></t>",
        )
        self._view("ns_outside", "<t><root><t t-call='base.ns_leaf'/></root></t>")
        qweb = self.env["ir.qweb"]
        inside = '<h:table xmlns:h="http://ex/t"><h:td>V</h:td></h:table>'
        outside = '<root><h:td xmlns:h="http://ex/t">V</h:td></root>'
        for order in (("ns_inside", "ns_outside"), ("ns_outside", "ns_inside")):
            self.env.registry.clear_cache("templates")
            for name in order:
                self.assertEqual(
                    str(qweb._render(f"base.{name}")),
                    inside if name == "ns_inside" else outside,
                    f"render order {order} changed the output of {name}",
                )
        etree.fromstring(str(qweb._render("base.ns_outside")))

    def test_signature_is_hashable_with_mapping_values(self):
        qweb = self.env["ir.qweb"]
        a = qweb.with_context(
            nsmap={"h": "u1", None: "u2"}
        )._get_template_cache_signature()
        b = qweb.with_context(
            nsmap={None: "u2", "h": "u1"}
        )._get_template_cache_signature()
        self.assertEqual(hash(a), hash(b))
        self.assertNotEqual(
            a, qweb.with_context(nsmap={"h": "other"})._get_template_cache_signature()
        )


class TestQWebDirectiveContracts(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": f"base.{key}", "arch_db": arch}
        )

    def test_t_set_slot_overrides_the_t_call_content(self):
        self._view("slot_callee", "<t>[<t t-out='0'/>]</t>")
        self._view(
            "slot_caller",
            "<t><t t-call='base.slot_callee'><t t-set='0'>OVERRIDE</t></t></t>",
        )
        self.assertEqual(
            str(self.env["ir.qweb"]._render("base.slot_caller")), "[OVERRIDE]"
        )

    def test_t_call_body_still_reaches_the_slot(self):
        self._view("slot_callee2", "<t>[<t t-out='0'/>]</t>")
        self._view("slot_caller2", "<t><t t-call='base.slot_callee2'>BODY</t></t>")
        self.assertEqual(
            str(self.env["ir.qweb"]._render("base.slot_caller2")), "[BODY]"
        )

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_deprecated_t_call_options_is_applied(self):
        self._view("co_leaf", "<t>[<!-- C --><t t-out='1'/>]</t>")
        self._view("co_none", "<t><t t-call='base.co_leaf'/></t>")
        self._view(
            "co_old",
            "<t><t t-call='base.co_leaf' t-call-options=\"{'preserve_comments': True}\"/></t>",
        )
        self._view(
            "co_new",
            "<t><t t-call='base.co_leaf' t-options=\"{'preserve_comments': True}\"/></t>",
        )
        qweb = self.env["ir.qweb"]
        self.assertEqual(str(qweb._render("base.co_none")), "[1]")
        self.assertEqual(str(qweb._render("base.co_new")), "[<!-- C -->1]")
        self.assertEqual(
            str(qweb._render("base.co_old")),
            "[<!-- C -->1]",
            "the deprecated spelling must behave like t-options",
        )

    def test_t_lang_does_not_duplicate_the_directive_walk(self):
        self._view("lang_leaf", "<t>L</t>")
        plain = self._view("lang_plain", "<t><t t-call='base.lang_leaf'/></t>")
        with_lang = self._view(
            "lang_set", "<t><t t-call='base.lang_leaf' t-lang=\"'en_US'\"/></t>"
        )
        qweb = self.env["ir.qweb"]
        marker = "yield QwebCallParameters("
        for view in (plain, with_lang):
            code = qweb._generate_code(view.id)[0]
            self.assertEqual(code.count(marker), 1)
            after_yield = code.split(marker, 1)[1].split("\n", 1)[1]
            self.assertTrue(
                after_yield.startswith("def "),
                f"dead code after the t-call yield:\n{after_yield[:200]}",
            )
        self.assertEqual(str(qweb._render(with_lang.id)), "L")

    def test_t_set_beside_an_output_directive_is_a_syntax_error(self):
        view = self._view("set_out", "<t><t t-set='a' t-value='1' t-out='2'/></t>")
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(view.id)
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)
        self.assertIn("t-set cannot share a node", str(cm.exception))

    def test_t_set_body_beside_an_output_directive_is_a_syntax_error(self):
        view = self._view("set_body_out", "<t><t t-set='a' t-out='v'>body</t></t>")
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(view.id, {"v": "V"})
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)
        self.assertIn("t-set cannot share a node", str(cm.exception))

    def test_t_set_slot_from_t_value_is_a_syntax_error(self):
        view = self._view("set_slot_value", "<t><t t-set='0' t-value='1'/></t>")
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(view.id)
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)
        self.assertIn('t-set="0" should not be set from t-value', str(cm.exception))

    def test_t_options_does_not_mutate_the_caller_dict(self):
        view = self._view("opt_alias", "<t><span t-out='v' t-options='opts'/></t>")
        opts = {"widget": "float"}
        self.env["ir.qweb"]._render(view.id, {"v": 1.5, "opts": opts})
        self.assertEqual(opts, {"widget": "float"})


class TestQWebExpressionFlattening(TransactionCase):
    def _render(self, arch, values=None):
        view = self.env["ir.ui.view"].create(
            {"name": "nl", "type": "qweb", "arch_db": arch}
        )
        return str(self.env["ir.qweb"]._render(view.id, values or {}))

    def test_newline_in_t_att_dict(self):
        self.assertEqual(
            self._render("<t><span t-att=\"{'a': 1,&#10;'b': 2}\">x</span></t>"),
            '<span a="1" b="2">x</span>',
        )

    def test_newline_in_t_foreach(self):
        self.assertEqual(
            self._render(
                "<t><t t-foreach='[1,&#10;2]' t-as='i'><t t-out='i'/></t></t>"
            ),
            "12",
        )

    def test_newline_in_t_args(self):
        self.env["ir.ui.view"].create(
            {
                "name": "argleaf",
                "type": "qweb",
                "key": "base.argleaf",
                "arch_db": "<t><t t-out='k'/><t t-out='j'/></t>",
            }
        )
        self.assertEqual(
            self._render(
                "<t><t t-call='base.argleaf' t-args=\"{'k': 1,&#10;'j': 2}\"/></t>"
            ),
            "12",
        )

    def test_newline_survives_a_view_serialisation_round_trip(self):
        el = etree.fromstring("<t><span t-att='x'/></t>")
        el[0].set("t-att", "{'a': 1,\n'b': 2}")
        arch = etree.tostring(el, encoding="unicode")
        self.assertIn("&#10;", arch)
        self.assertEqual(self._render(arch), '<span a="1" b="2"></span>')

    def test_multiline_string_literal_is_preserved_not_corrupted(self):
        self.assertEqual(
            self._render("<t><span t-att-title=\"'''a&#10;b'''\">x</span></t>"),
            '<span title="a\nb">x</span>',
        )


class TestQWebStandaloneBodyContent(TransactionCase):
    @staticmethod
    def _load(templates):
        def load(ref):
            return (etree.fromstring(templates[ref]), ref)

        return load

    def test_t_call_with_body_content(self):
        templates = {
            "m": "<t><t t-call='s'>BODY</t></t>",
            "s": "<t>[<t t-out='0'/>]</t>",
        }
        self.assertEqual(str(render("m", {}, self._load(templates))), "[BODY]")

    def test_t_set_with_body_content(self):
        templates = {"m": "<t><t t-set='a'>V</t><t t-out='a'/></t>"}
        self.assertEqual(str(render("m", {}, self._load(templates))), "V")

    def test_qweb_content_str_with_a_thread_dbname_set(self):
        templates = {
            "m": "<t><t t-call='s'><t t-set='x' t-value='1'/>BODY</t></t>",
            "s": "<t>[<t t-out='0'/>]</t>",
        }
        thread = threading.current_thread()
        had = hasattr(thread, "dbname")
        previous = getattr(thread, "dbname", None)
        thread.dbname = "some_other_db"
        try:
            self.assertEqual(str(render("m", {}, self._load(templates))), "[BODY]")
        finally:
            if had:
                thread.dbname = previous
            else:
                del thread.dbname

    def test_qweb_content_does_not_render_on_a_dunder_probe(self):
        content = QwebContent(
            self.env["ir.qweb"],
            QwebCallParameters({}, "r", None, None, False, "t-set", None),
        )
        with self.assertRaises(AttributeError):
            getattr(content, "__deepcopy__")  # noqa: B009 - the constant name is the subject: a dunder arriving by name must not render
        self.assertIsNone(content.html, "the snippet was rendered by a dunder probe")

    def test_non_template_argument_is_rejected(self):
        with self.assertRaises(TypeError):
            self.env["ir.qweb"]._generate_code(object())


class TestQWebStaticAttributes(TransactionCase):
    def _render(self, arch):
        view = self.env["ir.ui.view"].create(
            {"name": "sa", "type": "qweb", "arch_db": arch}
        )
        return str(self.env["ir.qweb"]._render(view.id))

    def test_translate_suffix_is_stripped_before_post_processing(self):
        seen = []
        original = type(self.env["ir.qweb"])._post_processing_att

        def spy(model, tagName, atts, *, is_static=False):
            seen.append(dict(atts))
            return original(model, tagName, atts, is_static=is_static)

        with patch.object(type(self.env["ir.qweb"]), "_post_processing_att", spy):
            out = self._render("<t><span title.translate='hi' class='c'>x</span></t>")
        self.assertEqual(out, '<span title="hi" class="c">x</span>')
        self.assertEqual(seen[0], {"title": "hi", "class": "c"})

    def test_attribute_names_are_escaped_on_the_static_path(self):
        original = type(self.env["ir.qweb"])._post_processing_att

        def inject(model, tagName, atts, *, is_static=False):
            atts = dict(atts)
            atts['x" onload="alert(1)'] = "1"
            return original(model, tagName, atts, is_static=is_static)

        with patch.object(type(self.env["ir.qweb"]), "_post_processing_att", inject):
            out = self._render("<t><span class='c'>x</span></t>")
        self.assertNotIn(' onload="alert(1)"', out)
        self.assertIn("&#34;", out)


@tagged("post_install", "-at_install")
class TestQWebRenderBatch(TransactionCase):
    def _tree(self, arch):
        return etree.fromstring(arch)

    def test_batch_matches_render_one_by_one(self):
        arch = '<t><p t-out="name"/><span t-if="shout">!</span></t>'
        varying = [
            {"name": "a", "shout": True},
            {"name": "b", "shout": False},
            {"name": "<b>c</b>", "shout": True},
        ]
        one_by_one = [
            self.env["ir.qweb"]._render(self._tree(arch), {"greeting": "hi", **values})
            for values in varying
        ]
        batched = self.env["ir.qweb"]._render_batch(
            self._tree(arch), {"greeting": "hi"}, varying
        )
        self.assertEqual([str(v) for v in batched], [str(v) for v in one_by_one])
        self.assertTrue(all(isinstance(v, markupsafe.Markup) for v in batched))

    def test_batch_does_not_leak_values_between_entries(self):
        arch = "<t><p t-out=\"only_first or 'none'\"/></t>"
        out = self.env["ir.qweb"]._render_batch(
            self._tree(arch), {"only_first": False}, [{"only_first": "x"}, {}]
        )
        self.assertEqual([str(v) for v in out], ["<p>x</p>", "<p>none</p>"])

    def test_batch_checks_the_varying_half_too(self):
        with self.assertRaises(TypeError):
            self.env["ir.qweb"]._render_batch(
                self._tree("<t><p>x</p></t>"), {}, [{"leak": ast}]
            )

    def test_batch_over_no_entries_is_no_renders(self):
        self.assertEqual(
            self.env["ir.qweb"]._render_batch(self._tree("<t><p>x</p></t>"), {}, []), []
        )

    def test_batch_reports_the_failing_entry_not_the_first(self):
        arch = '<t><p t-out="value.missing_attribute"/></t>'
        with self.assertRaises(QWebError):
            self.env["ir.qweb"]._render_batch(
                self._tree(arch),
                {},
                [{"value": {"missing_attribute": 1}}, {"value": 1}],
            )


class TestQWebCachedTemplateError(TransactionCase):
    @staticmethod
    def _traceback_length(error):
        length, traceback = 0, error.__traceback__
        while traceback is not None:
            length += 1
            traceback = traceback.tb_next
        return length

    def _cached_error(self, ref):
        return self.env["ir.ui.view"]._get_cached_template_info(ref)["error"]

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_render_of_a_missing_template_does_not_grow_its_traceback(self):
        qweb = self.env["ir.qweb"].with_context(raise_if_not_found=False)
        self.env.registry.clear_cache("templates")

        qweb._render("base.no_such_template_at_all", {})
        after_first = self._traceback_length(
            self._cached_error("base.no_such_template_at_all")
        )
        for _ in range(9):
            qweb._render("base.no_such_template_at_all", {})
        after_ten = self._traceback_length(
            self._cached_error("base.no_such_template_at_all")
        )

        self.assertEqual(
            after_ten,
            after_first,
            "the cached template error grew a traceback across renders: "
            f"{after_first} frames after one, {after_ten} after ten",
        )

    @mute_logger("odoo.addons.base.models.ir_qweb")
    def test_repeated_preloads_share_one_error_that_does_not_grow(self):
        View = self.env["ir.ui.view"].sudo()
        first = View._preload_views(["base.no_such_preloaded_template"])[
            "base.no_such_preloaded_template"
        ]["error"]
        second = View._preload_views(["base.no_such_preloaded_template"])[
            "base.no_such_preloaded_template"
        ]["error"]
        self.assertIs(first, second, "the batch cache stopped sharing the instance")

        qweb = self.env["ir.qweb"].with_context(raise_if_not_found=False)
        qweb._render("base.no_such_preloaded_template", {})
        after_first = self._traceback_length(first)
        for _ in range(9):
            qweb._render("base.no_such_preloaded_template", {})
        self.assertEqual(self._traceback_length(first), after_first)

    def test_get_template_view_does_not_raise_the_cached_instance(self):
        View = self.env["ir.ui.view"]
        seen = []
        original = type(View)._prepare_cached_template_error

        def spy(records, error):
            seen.append(error)
            return original(records, error)

        with (
            patch.object(type(View), "_prepare_cached_template_error", spy),
            self.assertRaises(MissingError),
        ):
            View._get_template_view("base.no_such_template_view")
        self.assertTrue(seen, "_get_template_view raised the cached instance directly")

    def test_raising_a_cached_error_never_mutates_it(self):
        error = MissingError("Template not found: 'x'")
        lengths = []
        for _ in range(5):
            with self.assertRaises(MissingError) as caught:
                raise self.env["ir.ui.view"]._prepare_cached_template_error(error)
            self.assertIsNot(caught.exception, error)
            lengths.append(self._traceback_length(caught.exception))
        self.assertEqual(
            len(set(lengths)), 1, f"each raise cost a frame more: {lengths}"
        )
        self.assertIsNone(
            error.__traceback__, "the shared instance accumulated a traceback"
        )

    def test_the_error_keeps_the_state_generate_code_reads(self):
        error = UserError("boom")
        error.context = {"view": self.env["ir.ui.view"]}
        with self.assertRaises(UserError) as caught:
            raise self.env["ir.ui.view"]._prepare_cached_template_error(error)
        self.assertIsNot(caught.exception, error)
        self.assertEqual(caught.exception.context, error.context)
        self.assertIsNone(error.__traceback__, "the cached instance was mutated")


class TestQWebDirectiveAliasesCompose(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": f"base.{key}", "arch_db": arch}
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = cls.env["res.users"].create(
            {
                "login": "qweb_groups_probe",
                "name": "qweb groups probe",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def test_groups_and_t_groups_on_one_node_both_apply(self):
        view = self._view(
            "groups_both",
            '<t><div t-groups="base.group_user" groups="base.group_system">'
            "SECRET</div></t>",
        )
        self.assertFalse(self.internal.has_group("base.group_system"))
        self.assertEqual(
            str(self.env["ir.qweb"].with_user(self.internal)._render(view.id)),
            "",
            "the `groups` restriction was dropped in favour of `t-groups`",
        )

    def test_groups_and_t_groups_on_one_node_render_when_both_pass(self):
        view = self._view(
            "groups_both_pass",
            '<t><div t-groups="base.group_user" groups="base.group_user">OK</div></t>',
        )
        self.assertEqual(
            str(self.env["ir.qweb"].with_user(self.internal)._render(view.id)),
            "<div>OK</div>",
        )

    def test_either_spelling_alone_still_works(self):
        for key, attr in (("groups_plain", "groups"), ("groups_t", "t-groups")):
            view = self._view(
                key, f'<t><div {attr}="base.group_system">SECRET</div></t>'
            )
            self.assertEqual(
                str(self.env["ir.qweb"].with_user(self.internal)._render(view.id)),
                "",
                f"@{attr} alone stopped restricting",
            )

    def test_t_if_and_t_elif_on_one_node_is_rejected(self):
        view = self._view(
            "if_elif_both",
            '<t><div t-if="False">A</div><div t-elif="True" t-if="False">B</div></t>',
        )
        with self.assertRaises(QWebError) as caught:
            self.env["ir.qweb"]._render(view.id)
        self.assertIn("t-elif", str(caught.exception))

    def test_a_valid_if_elif_chain_still_works(self):
        view = self._view(
            "if_elif_chain",
            '<t><div t-if="False">A</div><div t-elif="True">B</div>'
            '<div t-else="">C</div></t>',
        )
        self.assertEqual(str(self.env["ir.qweb"]._render(view.id)), "<div>B</div>")


class TestQWebOneOutputDirectivePerNode(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": f"base.{key}", "arch_db": arch}
        )

    def test_two_output_directives_on_one_node_are_rejected(self):
        for key, attrs in (
            ("out_esc", "t-out=\"'A'\" t-esc=\"'B'\""),
            ("out_raw", "t-out=\"'A'\" t-raw=\"'B'\""),
            ("esc_raw", "t-esc=\"'A'\" t-raw=\"'B'\""),
        ):
            view = self._view(key, f"<t><span {attrs}/></t>")
            with self.assertRaises(QWebError) as caught:
                self.env["ir.qweb"]._render(view.id)
            self.assertIn("only one output directive", str(caught.exception))

    def test_one_output_directive_is_unaffected(self):
        view = self._view("out_alone", "<t><span t-out=\"'A'\"/></t>")
        self.assertEqual(str(self.env["ir.qweb"]._render(view.id)), "<span>A</span>")


class TestQWebTwoSignaturesInOneRender(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": f"base.{key}", "arch_db": arch}
        )

    def setUp(self):
        super().setUp()
        self._view(
            "two_sig_root",
            """<t t-name="base.two_sig_root">
                <t t-set="msg"><!--C-->X</t>
                <t t-if="not depth">
                    <t t-call="base.two_sig_root" depth="1"
                       t-options="{'preserve_comments': True}"/>
                </t>
                <span t-out="msg"/>
            </t>""",
        )
        self.env.registry.clear_cache("templates")

    def _render(self, **values):
        return " ".join(
            str(self.env["ir.qweb"]._render("base.two_sig_root", values)).split()
        )

    def test_the_outer_frame_keeps_the_body_it_was_compiled_with(self):
        self.assertEqual(
            self._render(),
            "<span><!--C-->X</span> <span>X</span>",
            "the nested compile's body leaked into the outer frame",
        )

    def test_each_signature_alone_is_unchanged(self):
        self.assertEqual(self._render(depth=1), "<span>X</span>")
        self.env.registry.clear_cache("templates")
        self.assertEqual(
            " ".join(
                str(
                    self.env["ir.qweb"]
                    .with_context(preserve_comments=True)
                    ._render("base.two_sig_root", {"depth": 1})
                ).split()
            ),
            "<span><!--C-->X</span>",
        )


class TestQWebContentComparison(TransactionCase):
    def _render(self, arch, values=None):
        return str(self.env["ir.qweb"]._render(etree.fromstring(arch), values or {}))

    def test_a_body_equals_the_text_it_renders(self):
        self.assertEqual(
            self._render(
                "<t><t t-set='x'>AB</t>"
                "<t t-if=\"x == 'AB'\">EQ</t><t t-else=''>NEQ</t></t>"
            ),
            "EQ",
        )

    def test_a_t_value_string_is_unchanged(self):
        self.assertEqual(
            self._render(
                "<t><t t-set='x' t-value=\"'AB'\"/>"
                "<t t-if=\"x == 'AB'\">EQ</t><t t-else=''>NEQ</t></t>"
            ),
            "EQ",
        )

    def test_a_body_is_found_by_containment_and_by_key(self):
        self.assertEqual(
            self._render(
                "<t><t t-set='x'>AB</t>"
                "<t t-if=\"x in ['AB']\">IN</t><t t-else=''>OUT</t></t>"
            ),
            "IN",
        )
        self.assertEqual(
            self._render(
                "<t><t t-set='x'>AB</t><t t-out=\"{'AB': 'HIT'}.get(x, 'MISS')\"/></t>"
            ),
            "HIT",
        )

    def test_a_body_that_differs_still_compares_unequal(self):
        self.assertEqual(
            self._render(
                "<t><t t-set='x'>AB</t>"
                "<t t-if=\"x == 'ZZ'\">EQ</t><t t-else=''>NEQ</t></t>"
            ),
            "NEQ",
        )

    def test_the_operations_that_already_worked_still_do(self):
        self.assertEqual(
            self._render("<t><t t-set='x'>ABC</t><t t-out='len(x)'/></t>"), "3"
        )
        self.assertEqual(
            self._render("<t><t t-set='x'> AB </t>[<t t-out='x.strip()'/>]</t>"),
            "[AB]",
        )
        self.assertEqual(
            self._render(
                "<t><t t-set='x'></t><t t-if='x'>TRUE</t><t t-else=''>FALSE</t></t>"
            ),
            "FALSE",
        )

    def test_comparison_does_not_cost_laziness(self):
        rendered = []
        original = QwebContent.__str__

        def spy(content):
            if content.html is None:
                rendered.append(content)
            return original(content)

        with patch.object(QwebContent, "__str__", spy):
            out = self._render(
                "<t><t t-set='unused'>EXPENSIVE</t><span>only this</span></t>"
            )
        self.assertEqual(out, "<span>only this</span>")
        self.assertFalse(rendered, "an unreferenced t-set body was rendered")


class TestQWebWidgetBranding(TransactionCase):
    def _render(self, arch, **context):
        return str(
            self.env["ir.qweb"]
            .with_context(**context)
            ._render(etree.fromstring(arch), {})
        )

    ARCH = "<t><span t-out='1234.5' t-options-widget=\"'float'\"/></t>"

    def test_a_plain_render_publishes_no_branding(self):
        rendered = self._render(self.ARCH)
        self.assertNotIn("data-oe-expression", rendered)
        self.assertNotIn("data-oe-type", rendered)
        self.assertIn("1,234.5", rendered, "the widget stopped formatting")

    def test_the_editor_still_gets_its_branding(self):
        rendered = self._render(self.ARCH, inherit_branding=True)
        self.assertIn('data-oe-type="float"', rendered)
        self.assertIn('data-oe-expression="1234.5"', rendered)

    def test_a_widget_without_branding_still_reports_force_display(self):
        for branding in (True, False):
            values = {}
            _content, force_display = (
                self.env["ir.qweb"]
                .with_context(inherit_branding=branding)
                ._get_widget(1234.5, "1234.5", "span", {"widget": "float"}, values)
            )
            self.assertEqual(bool(force_display), branding)
            self.assertEqual(bool(values.get("__qweb_attrs__")), branding)


class TestQWebTranslationBoundary(TransactionCase):
    SOURCE_TERM = "Hello <b>world</b>"

    def setUp(self):
        super().setUp()
        self.env["res.lang"]._activate_lang("fr_FR")
        self.view = self.env["ir.ui.view"].create(
            {
                "name": "translation_boundary",
                "type": "qweb",
                "key": "base.translation_boundary",
                "arch": '<t t-name="base.translation_boundary">'
                f"<p>{self.SOURCE_TERM}</p></t>",
            }
        )

    def _render_fr(self, translation):
        self.view.update_field_translations(
            "arch_db", {"fr_FR": {self.SOURCE_TERM: translation}}
        )
        return str(
            self.env["ir.qweb"].with_context(lang="fr_FR")._render(self.view.id, {})
        )

    def test_an_entity_encoded_tag_never_becomes_live_markup(self):
        rendered = self._render_fr(
            "&lt;script&gt;alert(1)&lt;/script&gt;Bonjour <b>monde</b>"
        )
        self.assertNotIn("<script", rendered)
        self.assertIn(
            "Hello", rendered, "a refused translation falls back to the source"
        )

    def test_an_attribute_the_translator_adds_is_stripped(self):
        rendered = self._render_fr('Bonjour <b onclick="alert(2)" class="x">monde</b>')
        self.assertNotIn("onclick", rendered)
        self.assertIn('<b class="x">monde</b>', rendered)
        self.assertIn("Bonjour", rendered)

    def test_a_plain_translation_is_kept(self):
        self.assertIn("Bonjour <b>monde</b>", self._render_fr("Bonjour <b>monde</b>"))

    def test_the_adapter_applies_the_same_boundary(self):
        adapter = xml_term_adapter("Hello <b>world</b>")
        self.assertIsNone(adapter("&lt;script&gt;x&lt;/script&gt; <b>y</b>"))
        self.assertEqual(
            adapter('Salut <b onclick="alert(1)" title="t">monde</b>'),
            'Salut <b title="t">monde</b>',
        )
        self.assertEqual(
            adapter("a &lt; b <b>c</b>"),
            "a &lt; b <b>c</b>",
            "a bare less-than in text is not markup",
        )


class TestQWebErrorInfoSurvivesTName(TransactionCase):
    def _render_etree(self, arch):
        return str(self.env["ir.qweb"]._render(etree.fromstring(arch), {}))

    def test_an_etree_template_with_a_t_name_keeps_its_error_path(self):
        with self.assertRaises(QWebError) as cm:
            self._render_etree('<t t-name="base.named_etree"><p t-out="1/0"/></t>')
        qweb = cm.exception.qweb
        self.assertEqual(qweb.path, "/t/p")
        self.assertIn('t-out="1/0"', qweb.element or "")
        self.assertEqual(qweb.template, "base.named_etree")

    def test_an_etree_template_without_a_t_name_keeps_its_error_path(self):
        with self.assertRaises(QWebError) as cm:
            self._render_etree('<t><p t-out="1/0"/></t>')
        self.assertEqual(cm.exception.qweb.path, "/t/p")

    def test_content_between_t_if_and_t_else_is_refused_even_behind_a_comment(self):
        arch = '<t><t t-if="False">A</t><!-- c -->X<t t-else="">B</t></t>'
        with self.assertRaises(QWebError) as cm:
            self._render_etree(arch)
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)
        self.assertIn("between t-if and t-else", str(cm.exception))

    def test_a_comment_alone_between_t_if_and_t_else_is_fine(self):
        arch = '<t><t t-if="False">A</t><!-- c --> <t t-else="">B</t></t>'
        self.assertEqual(self._render_etree(arch), "B")


class TestQWebCompileErrorLocation(TransactionCase):
    def _view(self, key, arch):
        return self.env["ir.ui.view"].create(
            {"name": key, "type": "qweb", "key": key, "arch_db": arch}
        )

    def _render_error(self, template):
        with self.assertRaises(QWebError) as cm:
            self.env["ir.qweb"]._render(template, {})
        return cm.exception.qweb

    def test_a_called_template_that_does_not_compile_is_the_one_blamed(self):
        callee = self._view("base.cel_callee", '<t><p><t t-out="1 +"/></p></t>')
        caller = self._view(
            "base.cel_caller", '<t><div><t t-call="base.cel_callee"/></div></t>'
        )
        info = self._render_error("base.cel_caller")
        self.assertIn("Can not compile expression: 1 +", info.error)
        self.assertEqual(info.template, "base.cel_callee")
        self.assertEqual(info.ref, callee.id)
        self.assertEqual(info.path, "/t/p/t")
        self.assertEqual(info.element, '<t t-out="1 +"/>')
        self.assertEqual(
            info.source,
            [
                (caller.id, "/t/div/t", '<t t-call="base.cel_callee"/>'),
                (callee.id, "/t/p/t", '<t t-out="1 +"/>'),
            ],
        )

    def test_a_root_template_rendered_by_key_keeps_its_compile_location(self):
        view = self._view("base.cel_root", '<t><p><t t-out="1 +"/></p></t>')
        for template in ("base.cel_root", view.id):
            info = self._render_error(template)
            self.assertEqual((info.template, info.ref), ("base.cel_root", view.id))
            self.assertEqual(info.path, "/t/p/t")

    def test_an_etree_template_keeps_its_compile_location(self):
        info = self._render_error(etree.fromstring('<t><p><t t-out="1 +"/></p></t>'))
        self.assertEqual(info.template, "etree._Element")
        self.assertEqual(info.path, "/t/p/t")
        self.assertEqual(info.element, '<t t-out="1 +"/>')

    def test_the_slot_location_does_not_depend_on_the_compile_cache(self):
        self._view("base.cel_slot_callee", '<t><section><div t-out="0"/></section></t>')
        self._view(
            "base.cel_slot_wrap",
            '<div><t t-call="base.cel_slot_callee"><span t-out="a + b"/></t></div>',
        )
        self._view("base.cel_slot_top", '<div><t t-call="base.cel_slot_wrap"/></div>')
        cold = str(self._render_error("base.cel_slot_top"))
        warm = str(self._render_error("base.cel_slot_top"))
        self.assertEqual(cold, warm)
        self.assertIn("""'/t/section/div', '<div t-out="0"/>'""", cold)

    def test_a_parent_refused_after_its_children_is_the_element_named(self):
        info = self._render_error(
            etree.fromstring(
                '<t><t t-if="x"><span t-out="1"/></t>X<t t-else="">B</t></t>'
            )
        )
        self.assertIn("between t-if and t-else", info.error)
        self.assertEqual(info.path, "/t/t[1]")
        self.assertEqual(info.element, '<t t-if="x"/>')

    def test_a_namespaced_subtree_keeps_its_compile_location(self):
        info = self._render_error(
            etree.fromstring(
                '<t><svg xmlns="http://www.w3.org/2000/svg"><g t-out="1 +"/></svg></t>'
            )
        )
        self.assertEqual(
            info.element, '<g xmlns="http://www.w3.org/2000/svg" t-out="1 +"/>'
        )

    @mute_logger("odoo.db.cursor")
    def test_a_recoverable_database_error_is_not_wrapped(self):
        # Raised by psycopg under odoo/db/cursor.py, the frame walk of
        # _is_error_raised_in_qweb reaches the template's own frame; a helper
        # defined here would sit on the addons path and never be wrapped.
        from psycopg.errors import LockNotAvailable

        partner = self.env.ref(
            "base.main_partner"
        )  # committed, visible to a second cursor
        arch = etree.fromstring('<t><p t-out="env.cr.execute(q)"/></t>')
        query = f"SELECT id FROM res_partner WHERE id = {partner.id} FOR UPDATE NOWAIT"
        with self.registry.cursor() as other:
            other.execute(
                "SELECT id FROM res_partner WHERE id = %s FOR UPDATE NOWAIT",
                [partner.id],
            )
            with self.assertRaises(LockNotAvailable), self.env.cr.savepoint():
                self.env["ir.qweb"]._render(arch, {"q": query})
            other.rollback()


class TestQWebRenderScopedContext(TransactionCase):
    def test_a_growing_render_memo_does_not_change_the_context_hash(self):
        from odoo.tools import frozendict

        qweb = self.env["ir.qweb"]._render_prepare({}, {})
        context = qweb.env.context
        before = hash(frozendict(dict(context)))
        context["__qweb_loaded_codes"]["probe"] = "x" * 100_000
        context["__qweb_compiled_cache"][("probe", ())] = ({}, "probe", frozendict())
        context["_qweb_error_path_xml"][:] = ("probe", "/t", "<t/>")
        self.assertEqual(
            hash(frozendict(dict(context))),
            before,
            "the render memos are hashed by identity, not walked by content",
        )

    def test_a_caller_may_still_share_a_plain_dict_as_compiled_cache(self):
        shared = {}
        qweb = self.env["ir.qweb"].with_context(__qweb_compiled_cache=shared)
        qweb._render(etree.fromstring("<t>x</t>"), {})
        self.assertTrue(shared, "the caller's dict received the compiled template")


class TestQWebDirectiveEdgeCases(TransactionCase):
    def _render(self, arch, values=None):
        return str(self.env["ir.qweb"]._render(etree.fromstring(arch), values or {}))

    def _render_error(self, arch, values=None):
        with self.assertRaises(QWebError) as cm:
            self._render(arch, values)
        return str(cm.exception)

    def test_an_empty_groups_attribute_denies_like_has_groups(self):
        self.assertEqual(self._render('<t><div groups="">x</div></t>'), "")
        self.assertEqual(self._render('<t><div t-groups="">x</div></t>'), "")
        self.assertEqual(
            self._render('<t><div groups="base.group_user">x</div></t>'),
            "<div>x</div>",
        )

    def test_a_non_ascii_digit_is_not_a_repeat_count_nor_a_view_id(self):
        self.assertEqual(
            self._render('<t><t t-foreach="²" t-as="i">x</t></t>'),
            "",
            "a superscript is an (unset) variable name, not a repeat count",
        )
        self.assertEqual(self._render('<t><t t-foreach="3" t-as="i">x</t></t>'), "xxx")
        with self.assertRaises(MissingError):
            self._render('<t><t t-call="½"/></t>')
        with self.assertRaises(MissingError):
            self._render('<t><t t-call="²"/></t>')
        with self.assertRaises(MissingError):
            self._render('<t><t t-call="{{x}}"/></t>', {"x": "½"})

    def test_id_or_xmlid_converts_decimal_strings_only(self):
        from odoo.addons.base.models.ir_qweb import _id_or_xmlid

        for ref, expected in (
            ("12", 12),
            (12, 12),
            (" 12", " 12"),
            ("²", "²"),
            ("base.view", "base.view"),
        ):
            self.assertEqual(_id_or_xmlid(ref), expected)

    def test_a_t_node_without_an_attribute_reader_emits_no_attrs_reset(self):
        qweb = self.env["ir.qweb"]
        marker = "values['__qweb_attrs__'] = {}"
        code = qweb._generate_code(etree.fromstring('<t><t t-if="x">y</t></t>'))[0]
        self.assertNotIn(marker, code)
        code = qweb._generate_code(etree.fromstring('<t><span t-if="x">y</span></t>'))[
            0
        ]
        self.assertEqual(code.count(marker), 1)
        code = qweb._generate_code(
            etree.fromstring('<t><t t-if="x" t-att-a="f()"/></t>')
        )[0]
        self.assertNotIn("attrs['a']", code, "nothing receives an attribute on <t>")
        self.assertNotIn("__qweb_attrs__", code)
        self.assertEqual(
            self._render(
                '<t><t t-if="v" t-out="v" t-options-widget="\'float\'"/></t>',
                {"v": 1.5},
            ),
            "1.5",
        )

    def test_namespace_declarations_are_emitted_in_a_fixed_order(self):
        arch = (
            '<t><svg xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns="http://www.w3.org/2000/svg" xmlns:a="urn:a"><g t-if="v"/></svg></t>'
        )
        self.assertEqual(
            self._render(arch, {"v": True}),
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:a="urn:a" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"><g></g></svg>',
        )

    def test_a_widget_gets_no_value_like_a_field_does(self):
        for widget in ("integer", "float", "time", "duration", "relative", "image_url"):
            for value in (None, False):
                arch = f"<t><span t-out='v' t-options-widget=\"'{widget}'\">none</span></t>"
                self.assertEqual(
                    self._render(arch, {"v": value}),
                    "<span>none</span>",
                    f"{widget} with {value!r} must show the default body",
                )
        self.assertEqual(
            self._render(
                "<t><span t-out='v' t-options-widget=\"'integer'\"/></t>", {"v": 0}
            ),
            "<span>0</span>",
        )
        self.assertEqual(
            self._render(
                "<t>[<span t-out='v' t-options-widget=\"'many2one'\"/>]</t>",
                {"v": self.env["res.partner"]},
            ),
            "[]",
            "an empty widget value renders no tag, like a plain t-out",
        )

    def test_t_options_shapes_merge_into_one_dict(self):
        arch = "<t><span t-out='v' t-options=\"{'widget': 'float'}\" t-options-precision='1'/></t>"
        self.assertEqual(self._render(arch, {"v": 1.25}), "<span>1.3</span>")
        arch = "<t><span t-out='v' t-options-widget=\"'float'\" t-options-precision='3'/></t>"
        self.assertEqual(self._render(arch, {"v": 1.25}), "<span>1.250</span>")

    def test_the_generated_module_is_flat_and_its_line_numbers_are_true(self):
        qweb = self.env["ir.qweb"]
        arch = '<t t-name="base.flat"><p>a</p><p>b</p><t t-out="1/0"/></t>'
        code = qweb._generate_code(etree.fromstring(arch))[0]
        self.assertNotIn("generate_functions", code)
        with self.assertRaises(QWebError) as cm:
            self._render(arch)
        lines = code.split("\n")
        error_line = [
            trace.tb_lineno
            for trace in iter_traceback(cm.exception.__cause__)
            if trace.tb_frame.f_code.co_filename == "<base.flat>"
        ][-1]
        self.assertIn("1/0", lines[error_line - 1])
        self.assertEqual(cm.exception.qweb.path, "/t/t")


def iter_traceback(error):
    trace = error.__traceback__
    while trace is not None:
        yield trace
        trace = trace.tb_next
