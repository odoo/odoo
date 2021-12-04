# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon

import base64

from lxml import etree


class AccountTestEdiCommon(AccountTestInvoicingCommon):

    def assertXmlTreeEqual(self, xml_tree, expected_xml_tree):
        ''' Compare two lxml.etree.
        :param xml_tree:            The current tree.
        :param expected_xml_tree:   The expected tree.
        '''

        def _turn_node_as_dict_hierarchy(node):
            ''' Turn the node as a python dictionary to be compared later with another one.
            Allow to ignore the management of namespaces.
            :param node:    A node inside an xml tree.
            :return:        A python dictionary.
            '''
            tag_split = node.tag.split('}')
            tag_wo_ns = tag_split[-1]
            attrib_wo_ns = {k: v for k, v in node.attrib.items() if '}' not in k}
            return {
                'tag': tag_wo_ns,
                'namespace': None if len(tag_split) < 2 else tag_split[0],
                'text': (node.text or '').strip(),
                'attrib': attrib_wo_ns,
                'children': [_turn_node_as_dict_hierarchy(child_node) for child_node in node.getchildren()],
            }

        def assertNodeDictEqual(node_dict, expected_node_dict):
            ''' Compare nodes created by the `_turn_node_as_dict_hierarchy` method.
            :param node_dict:           The node to compare with.
            :param expected_node_dict:  The expected node.
            '''
            # Check tag.
            self.assertEqual(node_dict['tag'], expected_node_dict['tag'])

            # Check attributes.
            node_dict_attrib = {k: '___ignore___' if expected_node_dict['attrib'].get(k) == '___ignore___' else v
                                for k, v in node_dict['attrib'].items()}
            expected_node_dict_attrib = {k: v for k, v in expected_node_dict['attrib'].items() if v != '___remove___'}
            self.assertDictEqual(
                node_dict_attrib,
                expected_node_dict_attrib,
                "Element attributes are different for node %s" % node_dict['tag'],
            )

            # Check text.
            if expected_node_dict['text'] != '___ignore___':
                self.assertEqual(
                    node_dict['text'],
                    expected_node_dict['text'],
                    "Element text are different for node %s" % node_dict['tag'],
                )

            # Check children.
            self.assertEqual(
                [child['tag'] for child in node_dict['children']],
                [child['tag'] for child in expected_node_dict['children']],
                "Number of children elements for node %s is different." % node_dict['tag'],
            )

            for child_node_dict, expected_child_node_dict in zip(node_dict['children'], expected_node_dict['children']):
                assertNodeDictEqual(child_node_dict, expected_child_node_dict)

        assertNodeDictEqual(
            _turn_node_as_dict_hierarchy(xml_tree),
            _turn_node_as_dict_hierarchy(expected_xml_tree),
        )

    def with_applied_xpath(self, xml_tree, xpath):
        ''' Applies the xpath to the xml_tree passed as parameter.
        :param xml_tree:    An instance of etree.
        :param xpath:       The xpath to apply as a string.
        :return:            The resulting etree after applying the xpaths.
        '''
        diff_xml_tree = etree.fromstring('<data>%s</data>' % xpath)
        return self.env['ir.ui.view'].apply_inheritance_specs(xml_tree, diff_xml_tree, None)

    def get_xml_tree_from_attachment(self, attachment):
        ''' Extract an instance of etree from an ir.attachment.
        :param attachment:  An ir.attachment.
        :return:            An instance of etree.
        '''
        return etree.fromstring(base64.b64decode(attachment.with_context(bin_size=False).datas))

    def get_xml_tree_from_string(self, xml_tree_str):
        ''' Convert the string passed as parameter to an instance of etree.
        :param xml_tree_str:    A string representing an xml.
        :return:                An instance of etree.
        '''
        return etree.fromstring(xml_tree_str)
