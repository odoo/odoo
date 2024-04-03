# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from __future__ import absolute_import
import os
import unittest
import ebaysdk.shopping
import lxml

os.environ.setdefault("EBAY_YAML", "ebay.yaml")

class TestErrors(unittest.TestCase):

    def DISABLE_test_single_item(self):
        connection = ebaysdk.shopping.Connection(version='799', config_file=os.environ.get('EBAY_YAML'))

        for i in range(20):
            connection.execute('GetSingleItem', {
                'ItemID': '262809803926',
                'version': '981',
                'IncludeSelector': ['Variations']
            })
            self.assertEqual(connection.response.status_code, 200)
            self.assertEqual(type(connection.response.dom()), lxml.etree._Element)

if __name__ == '__main__':
    unittest.main()

"""
<?xml version='1.0' encoding='utf-8'?><GetSingleItemRequest xmlns="urn:ebay:apis:eBLBaseComponents"><IncludeSelector>Variations</I
ncludeSelector><ItemID>262809803926</ItemID><version>981</version></GetSingleItemRequest>
2017-02-28 06:18:42,156 ebaysdk [DEBUG]:total time=0.478377819061
2017-02-28 06:18:42,156 ebaysdk [DEBUG]:execute: verb=GetSingleItem data={'ItemID': '262809803926', 'version': 981, 'IncludeSelector': 'Variations'}
2017-02-28 06:18:42,157 ebaysdk [DEBUG]:REQUEST (3ff5f071-04c3-40c0-a4f0-57f04a9e9972): POST http://open.api.ebay.com/shopping
2017-02-28 06:18:42,157 ebaysdk [DEBUG]:headers={'Content-Length': '219', 'X-EBAY-API-REQUEST-ENCODING': 'XML', 'X-EBAY-API-VERSION': '799', 'User-Agent': 'eBaySDK/2.1.4 Pytho
n/2.7.6 Linux/3.13.0-91-generic', 'X-EBAY-SDK-REQUEST-ID': '3ff5f071-04c3-40c0-a4f0-57f04a9e9972', 'X-EBAY-API-SITE-ID': '0', 'X-EBAY-API-CALL-NAME': 'GetSingleItem', 'Content
-Type': 'text/xml', 'X-EBAY-API-APP-ID': 'LogoGrab-logograb-PRD-42f530923-a70f22b2'}
2017-02-28 06:18:42,157 ebaysdk [DEBUG]:body=<?xml version='1.0' encoding='utf-8'?><GetSingleItemRequest xmlns="urn:ebay:apis:eBLBaseComponents"><IncludeSelector>Variations</I
ncludeSelector><ItemID>262809803926</ItemID><version>981</version></GetSingleItemRequest>
2017-02-28 06:18:42,511 ebaysdk [DEBUG]:RESPONSE (3ff5f071-04c3-40c0-a4f0-57f04a9e9972):
2017-02-28 06:18:42,511 ebaysdk [DEBUG]:elapsed time=0:00:00.354254
2017-02-28 06:18:42,511 ebaysdk [DEBUG]:status code=500
2017-02-28 06:18:42,511 ebaysdk [DEBUG]:headers={'breadcrumbid': 'ID-slc4b03c-6483-stratus-slc-ebay-com-53764-1487075486325-0-1105919761', 'content-length': '25', 'accept-enco
ding': 'identity', 'x-ebay-api-request-encoding': 'XML', 'x-ebay-api-version': '799', 'user-agent': 'eBaySDK/2.1.4 Python/2.7.6 Linux/3.13.0-91-generic', 'connection': 'keep-a
live', 'x-ebay-sdk-request-id': '3ff5f071-04c3-40c0-a4f0-57f04a9e9972', 'x-ebay-api-site-id': '0', 'x-ebay-api-call-name': 'GetSingleItem', 'content-type': 'text/plain;charset
=utf-8', 'x-forwarded-for': '52.19.146.95', 'x-ebay-api-app-id': 'LogoGrab-logograb-PRD-42f530923-a70f22b2'}
2017-02-28 06:18:42,511 ebaysdk [DEBUG]:content=an internal error occured
2017-02-28 06:18:42,512 ebaysdk [DEBUG]:response parse failed: Start tag expected, '<' not found, line 1, column 1
ERROR - 2017-02-28 06:18:42,512 - utils.firehose_util - MainProcess - MainThread: Shopping Call error: {"ItemID": "262809803926", "version": 981, "IncludeSelector": "Variation
s"}
Traceback (most recent call last):
  File "/home/ubuntu/logograb2-detection-server/utils/firehose_util.py", line 235, in make_ebay_request
    r = Shopping(appid=app_id, config_file=None, debug=True).execute('GetSingleItem', api_pars)
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/connection.py", line 124, in execute
    self.error_check()
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/connection.py", line 209, in error_check
    estr = self.error()
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/connection.py", line 321, in error
    error_array.extend(self._get_resp_body_errors())
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/shopping/__init__.py", line 188, in _get_resp_body_errors
    dom = self.response.dom()
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/response.py", line 233, in dom
    return self._dom
  File "/usr/local/lib/python2.7/dist-packages/ebaysdk/response.py", line 220, in __getattr__
    return getattr(self._obj, name)
AttributeError: 'Response' object has no attribute '_dom'
"""
