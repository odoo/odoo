# -*- coding: utf-8 -*-
import unittest2

import mock

from openerp import http

class MockRequestCase(unittest2.TestCase):
    def setUp(self):
        super(MockRequestCase, self).setUp()
        http._request_stack.push(mock.Mock())

    def tearDown(self):
        http._request_stack.pop()
        super(MockRequestCase, self).tearDown()

