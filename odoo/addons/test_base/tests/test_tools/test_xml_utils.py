# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, common
from odoo.tools.xml_utils import _check_with_xsd

from lxml.etree import XMLSchemaError


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestLXML(common.TransactionCase):
    def test_lxml_import_from_filestore(self):
        resolver_schema_int = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                        xmlns:etype="http://codespeak.net/lxml/test/external">
                <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="imported_schema.xsd"/>
                <xsd:element name="a" type="etype:AType"/>
            </xsd:schema>
        """

        incomplete_schema_int = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                        xmlns:etype="http://codespeak.net/lxml/test/external">
                <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="non_existing_schema.xsd"/>
                <xsd:element name="a" type="etype:AType"/>
            </xsd:schema>
        """

        imported_schema = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                        targetNamespace="http://codespeak.net/lxml/test/external">
                <xsd:complexType name="AType">
                    <xsd:sequence><xsd:element name="b" type="xsd:string" minOccurs="0" maxOccurs="unbounded"/></xsd:sequence>
                </xsd:complexType>
            </xsd:schema>
        """

        self.env['ir.attachment'].create([{
            'raw': resolver_schema_int,
            'name': 'resolver_schema_int.xsd'
        }, {
            'raw': incomplete_schema_int,
            'name': 'incomplete_schema_int.xsd'
        }, {
            'raw': imported_schema,
            'name': 'imported_schema.xsd'
        }])

        _check_with_xsd("<a><b></b></a>", 'resolver_schema_int.xsd', self.env)

        with self.assertRaises(XMLSchemaError):
            _check_with_xsd("<a><b></b></a>", 'incomplete_schema_int.xsd', self.env)

        with self.assertRaises(FileNotFoundError):
            _check_with_xsd("<a><b></b></a>", 'non_existing_schema.xsd', self.env)
