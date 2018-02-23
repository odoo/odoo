import unittest
import openerp.tests

class WebSuite(openerp.tests.HttpCase):

    @unittest.skip('Memory leak in this test lead to phantomjs crash, making it unreliable')
    def test_01_js(self):
        self.phantom_js('/web/tests?mod=web',"","", login='admin')
