# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from __future__ import absolute_import
import os
import sys
import unittest
import doctest
import ebaysdk.utils
import ebaysdk.config
import ebaysdk.response
import ebaysdk.connection
import ebaysdk.http
import ebaysdk.shopping
import ebaysdk.trading
import ebaysdk.merchandising
import ebaysdk.soa.finditem
import ebaysdk.finding
import ebaysdk.poller.orders
import ebaysdk.inventorymanagement

# does not pass with python3.3
try:
    import ebaysdk.parallel
except ImportError:
    pass

# os.environ.setdefault("EBAY_YAML", "ebay.yaml")


class TestBase(unittest.TestCase):

    def doctest(self, module):
        doctest.testmod(module, raise_on_error=True, verbose=False)

    def test_run_doctest_poller(self):
        self.doctest(ebaysdk.poller.orders)

    def test_run_doctest_utils(self):
        self.doctest(ebaysdk.utils)

    def test_run_doctest_config(self):
        self.doctest(ebaysdk.config)

    def test_run_doctest_response(self):
        self.doctest(ebaysdk.response)

    def test_run_doctest_connection(self):
        self.doctest(ebaysdk.connection)

    def test_run_doctest_shopping(self):
        s = ebaysdk.shopping.Connection(config_file=os.environ.get('EBAY_YAML'))
        resp = s.execute('GetCategoryInfo',
            {'CategoryID': '-1',
             'IncludeSelector': ['ChildCategories']})
        self.assertEqual(s.response.reply.Ack, 'Success')
        self.assertEqual(s.error(), None)
        #self.doctest(ebaysdk.shopping)

    def test_run_doctest_trading(self):
        self.doctest(ebaysdk.trading)

    def test_run_doctest_merchandising(self):
        self.doctest(ebaysdk.merchandising)

    def test_run_doctest_finding(self):
        self.doctest(ebaysdk.finding)

    def test_run_doctest_inventorymanagement(self):
        self.doctest(ebaysdk.inventorymanagement)

    def test_grequests(self):
        if not sys.version_info[0] >= 3 \
            and sys.modules.has_key('grequests') is True:

            # self.doctest(ebaysdk.parallel)
            pass

if __name__ == '__main__':
    unittest.main()
