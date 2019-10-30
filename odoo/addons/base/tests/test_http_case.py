# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger
from unittest.mock import patch

@tagged('-at_install', 'post_install')
class TestHttpCase(HttpCase):

    def test_console_error_string(self):
        with self.assertRaises(AssertionError) as error_catcher:
            code = "console.error('test error','message')"
            with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                self.browser_js(url_path='about:blank', code=code)
        # second line must contains error message
        self.assertEqual(error_catcher.exception.args[0].split('\n', 1)[1], "test error message")

    def test_console_error_object(self):
        with self.assertRaises(AssertionError) as error_catcher:
            code = "console.error(TypeError('test error ' + 'message'))"
            with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                self.browser_js(url_path='about:blank', code=code)
        # second line must contains error message
        self.assertEqual(error_catcher.exception.args[0].split('\n', 1)[1],
        'TypeError: test error message\n    at <anonymous>:1:15')

    def test_console_log_object(self):
        with self.assertLogs() as log_catcher:
            code = "console.log({custom:{1:'test', 2:'a'}, value:1, description:'dummy'});console.log('test successful');"
            self.browser_js(url_path='about:blank', code=code)
        console_log_count = 0
        for log in log_catcher.output:
            if 'console log' in log:
                text = log.split('console log: ', 1)[1]
                if text == 'test successful':
                    continue
                self.assertEqual(log.split('console log: ', 1)[1], "Object\n{custom:Object, value:1, description:'dummy'}")
                console_log_count +=1
        self.assertEqual(console_log_count, 1)
