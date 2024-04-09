# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from __future__ import absolute_import
import os
import unittest
import re
from ebaysdk.utils import dict2xml

os.environ.setdefault("EBAY_YAML", "ebay.yaml")


class TestBase(unittest.TestCase):

    def test_motors_compat_request_xml(self):
        motors_dict = {
            'Item': {
                'Category': '101',
                'Title': 'My Title',
                'ItemCompatibilityList': {
                    'Compatibility': [
                        {
                            'CompatibilityNotes': 'Fits for all trims and engines.',
                            'NameValueList': [
                                {'Name': 'Year', 'Value': '2001'},
                                {'Name': 'Make', 'Value': 'Honda'},
                                {'Name': 'Model', 'Value': 'Accord'}
                            ]
                        },
                    ]
                }
            }
        }

        motors_xml = """<Item>
    <Category>101</Category>
    <ItemCompatibilityList>
        <Compatibility>
            <CompatibilityNotes>Fits for all trims and engines.</CompatibilityNotes>
            <NameValueList>
                <Name>Year</Name><Value>2001</Value>
            </NameValueList>
            <NameValueList>
                <Name>Make</Name><Value>Honda</Value>
            </NameValueList>
            <NameValueList>
                <Name>Model</Name><Value>Accord</Value>
            </NameValueList>
        </Compatibility>
    </ItemCompatibilityList>
    <Title>My Title</Title>
</Item> 
        """

        motors_xml = re.sub(r'>\s+<', '><', motors_xml)
        motors_xml = re.sub(r'\s+$', '', motors_xml)

        self.assertEqual(dict2xml(motors_dict), motors_xml)


if __name__ == '__main__':
    unittest.main()
