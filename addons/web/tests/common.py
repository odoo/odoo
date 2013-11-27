# -*- coding: utf-8 -*-
import unittest2

import mock

from openerp import http

class MockRequestCase(unittest2.TestCase):
    def setUp(self):
        super(MockRequestCase, self).setUp()
        self.tmp_req = mock.Mock()
        http._request_stack.push(self.tmp_req)

    def tearDown(self):
        http._request_stack.pop()
        super(MockRequestCase, self).tearDown()

