from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.addons.account.tools import dict_to_xml


@tagged('post_install', '-at_install')
class TestDictToXml(TransactionCase):
    def assertXmlEqual(self, element1, element2):
        self.assertEqual(etree.tostring(element1), etree.tostring(element2))

    def test_10_empty_node(self):
        element = dict_to_xml(node={}, tag='Node')
        self.assertIsNone(element)

    def test_11_render_empty_node(self):
        element = dict_to_xml(node={}, tag='Node', render_empty_nodes=True)
        self.assertXmlEqual(element, etree.fromstring('<Node/>'))

    def test_21_simple_node(self):
        node = {
            '_tag': 'Node',
            '_text': 'content',
            '_comment': 'comment',
            'attribute1': 'value1',
            'attribute2': None,
        }
        element = dict_to_xml(node)
        self.assertXmlEqual(element, etree.fromstring('<Node attribute1="value1">content</Node>'))

    def test_22_simple_node_with_nsmap(self):
        node = {
            '_tag': 'ns1:Node',
            '_text': 'content',
            '_comment': 'comment',
            'attribute1': 'value1',
            'ns2:attribute2': 'value2',
            'ns2:attribute3': None,
        }
        nsmap = {
            None: 'urn:ns0',
            'ns1': 'urn:ns1',
            'ns2': 'urn:ns2',
        }
        element = dict_to_xml(node, nsmap=nsmap)
        self.assertXmlEqual(element, etree.fromstring(
            '<ns1:Node xmlns="urn:ns0" xmlns:ns1="urn:ns1" xmlns:ns2="urn:ns2" attribute1="value1" ns2:attribute2="value2">'
            'content</ns1:Node>'
        ))

    def test_31_compound_node(self):
        node = {
            '_tag': 'Parent',
            'Child1': {
                '_text': 'content 1',
                'attribute1': 'value1',
            },
            'Child2': {
                '_text': None,
                'attribute2': None,
            },
            'Child3': [
                {
                    'attribute3': 'value3',
                },
                {
                    'attribute4': 'value4',
                },
            ],
        }
        element = dict_to_xml(node)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent><Child1 attribute1="value1">content 1</Child1>'
            '<Child3 attribute3="value3"/><Child3 attribute4="value4"/>'
            '</Parent>'
        ))

    def test_32_compound_node_render_empty_nodes(self):
        node = {
            '_tag': 'Parent',
            'Child1': {
                '_text': 'content 1',
                'attribute1': 'value1',
            },
            'Child2': {
                '_text': None,
                'attribute2': None,
            },
            'Child3': [
                {
                    'attribute3': 'value3',
                },
                {
                    'attribute4': None,
                },
                None,
            ],
        }
        element = dict_to_xml(node, render_empty_nodes=True)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent><Child1 attribute1="value1">content 1</Child1>'
            '<Child2/>'
            '<Child3 attribute3="value3"/>'
            '<Child3/>'
            '</Parent>'
        ))

    def test_33_compound_node_with_template(self):
        node = {
            '_tag': 'Parent',
            'Child3': [
                {
                    'attribute3': 'value3',
                },
                {
                    'attribute4': 'value4',
                },
                None,
            ],
            'Child2': {
                '_text': None,
                'attribute2': None,
            },
            'Child1': {
                '_text': 'content 1',
                'attribute1': 'value1',
            },
        }
        template = {
            'Child1': {},
            'Child3': {},
        }
        element = dict_to_xml(node, template=template)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent><Child1 attribute1="value1">content 1</Child1>'
            '<Child3 attribute3="value3"/>'
            '<Child3 attribute4="value4"/>'
            '</Parent>'
        ))

    def test_34_compound_node_with_template_raises(self):
        node = {
            '_tag': 'Parent',
            'Child3': [
                {
                    'attribute3': 'value3',
                },
                {
                    'attribute4': 'value4',
                },
                None,
            ],
            'UnknownChild': {
                '_text': 'something',
            },
            'Child1': {
                '_text': 'content 1',
                'attribute1': 'value1',
            },
        }
        template = {
            'Child1': {},
            'Child3': {},
        }
        with self.assertRaises(ValueError):
            dict_to_xml(node, template=template)

    def test_35_compound_node_with_template_and_nsmap(self):
        node = {
            '_tag': 'Parent',
            'ns3:Child3': [
                {
                    'attribute3': 'value3',
                },
                {
                    'attribute4': 'value4',
                },
                None,
            ],
            'ns2:Child2': {
                '_text': None,
                'attribute2': None,
            },
            'ns1:Child1': {
                '_text': 'content 1',
                'attribute1': 'value1',
            },
        }
        template = {
            'ns1:Child1': {},
            'ns3:Child3': {},
        }
        nsmap = {
            None: 'urn:ns0',
            'ns1': 'urn:ns1',
            'ns2': 'urn:ns2',
            'ns3': 'urn:ns3',
        }
        element = dict_to_xml(node, template=template, nsmap=nsmap)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent xmlns="urn:ns0" xmlns:ns1="urn:ns1" xmlns:ns2="urn:ns2" xmlns:ns3="urn:ns3">'
            '<ns1:Child1 attribute1="value1">content 1</ns1:Child1>'
            '<ns3:Child3 attribute3="value3"/>'
            '<ns3:Child3 attribute4="value4"/>'
            '</Parent>'
        ))

    def test_40_complex_example(self):
        node = {
            '_tag': 'Parent',
            '_comment': 'comment',
            'ns1:Child1': [
                {
                    'ns2:attribute1': 'value1',
                    'ns3:SubChild1': {
                        '_text': 'content 1',
                        'attribute2': 'value2',
                    },
                    'ns3:SubChild2': {
                        '_text': None,
                    },
                },
                {
                    'ns2:attribute2': None,
                    'ns3:Subchild3': {
                        '_text': None
                    },
                },
                None,
            ],
        }
        template = {
            'ns1:Child1': {
                'ns3:SubChild1': {},
            },
        }
        nsmap = {
            None: 'urn:ns0',
            'ns1': 'urn:ns1',
            'ns2': 'urn:ns2',
            'ns3': 'urn:ns3',
        }
        element = dict_to_xml(node, template=template, nsmap=nsmap)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent xmlns="urn:ns0" xmlns:ns1="urn:ns1" xmlns:ns2="urn:ns2" xmlns:ns3="urn:ns3">'
            '<ns1:Child1 ns2:attribute1="value1">'
            '<ns3:SubChild1 attribute2="value2">content 1</ns3:SubChild1>'
            '</ns1:Child1>'
            '</Parent>'
        ))

    def test_41_complex_example_render_empty_nodes(self):
        node = {
            '_tag': 'Parent',
            '_comment': 'comment',
            'ns1:Child1': [
                {
                    'ns2:attribute1': 'value1',
                    'ns3:SubChild1': {
                        '_text': 'content 1',
                        'attribute2': 'value2',
                    },
                    'ns3:SubChild2': {
                        '_text': None,
                    },
                },
                {
                    'ns2:attribute2': None,
                    'ns3:Subchild3': {
                        '_text': None
                    },
                },
                None,
            ],
        }
        template = {
            'ns1:Child1': {
                'ns3:SubChild1': {},
                'ns3:SubChild2': {},
                'ns3:Subchild3': {},
            },
        }
        nsmap = {
            None: 'urn:ns0',
            'ns1': 'urn:ns1',
            'ns2': 'urn:ns2',
            'ns3': 'urn:ns3',
        }
        element = dict_to_xml(node, template=template, render_empty_nodes=True, nsmap=nsmap)
        self.assertXmlEqual(element, etree.fromstring(
            '<Parent xmlns="urn:ns0" xmlns:ns1="urn:ns1" xmlns:ns2="urn:ns2" xmlns:ns3="urn:ns3">'
            '<ns1:Child1 ns2:attribute1="value1">'
            '<ns3:SubChild1 attribute2="value2">content 1</ns3:SubChild1>'
            '<ns3:SubChild2/>'
            '</ns1:Child1>'
            '<ns1:Child1>'
            '<ns3:Subchild3/>'
            '</ns1:Child1>'
            '</Parent>'
        ))
