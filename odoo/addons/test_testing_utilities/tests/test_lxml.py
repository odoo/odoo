import base64

from lxml.etree import XMLSchemaError

from odoo.tests.common import TransactionCase
from odoo.tools.xml_utils import _check_with_xsd


class TestLXML(TransactionCase):

    def test_lxml_import_from_filestore(self):
        resolver_schema_int = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:etype="http://codespeak.net/lxml/test/external">
                <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="imported_schema.xsd"/>
                <xsd:element name="a" type="etype:AType"/>
            </xsd:schema>
        """

        imported_schema = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" targetNamespace="http://codespeak.net/lxml/test/external">
                <xsd:complexType name="AType">
                    <xsd:sequence>
                        <xsd:element name="b" type="xsd:string" minOccurs="0" maxOccurs="unbounded"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:schema>
        """

        self.env['ir.attachment'].create([{
            'datas': base64.b64encode(resolver_schema_int),
            'name': 'resolver_schema_int.xsd',
        }, {
            'datas': base64.b64encode(imported_schema),
            'name': 'imported_schema.xsd',
        }])

        _check_with_xsd("<a><b></b></a>", 'resolver_schema_int.xsd', self.env)

    def test_lxml_import_from_filestore_with_incomplete_schema(self):
        incomplete_schema_int = b"""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:etype="http://codespeak.net/lxml/test/external">
                <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="non_existing_schema.xsd"/>
                <xsd:element name="a" type="etype:AType"/>
            </xsd:schema>
        """

        self.env['ir.attachment'].create([{
            'datas': base64.b64encode(incomplete_schema_int),
            'name': 'incomplete_schema_int.xsd',
        }])

        with self.assertRaises(XMLSchemaError):
            _check_with_xsd("<a><b></b></a>", 'incomplete_schema_int.xsd', self.env)

    def test_lxml_import_from_filestore_with_non_existing_schema(self):
        with self.assertRaises(FileNotFoundError):
            _check_with_xsd("<a><b></b></a>", 'non_existing_schema.xsd', self.env)
