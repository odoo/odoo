# -*- coding: utf-8 -*-
import unittest2

import mock

from openerp import http

class MockRequestCase(unittest2.TestCase):
    def setUp(self):
        super(MockRequestCase, self).setUp()
        self.tmp_req = http.set_request(mock.Mock())
        self.tmp_req.__enter__()

    def tearDown(self):
        self.tmp_req.__exit__(None, None, None)
        super(MockRequestCase, self).tearDown()

