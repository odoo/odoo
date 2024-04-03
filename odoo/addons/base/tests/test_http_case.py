# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged, ChromeBrowser
from odoo.tools import config, logging
from unittest.mock import patch

@tagged('-at_install', 'post_install')
class TestHttpCase(HttpCase):

    def test_console_error_string(self):
        with self.assertLogs(level='ERROR') as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error('test error','message')"
                with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                    self.browser_js(url_path='about:blank', code=code)
            # second line must contains error message
            self.assertEqual(error_catcher.exception.args[0].splitlines()[-1], "test error message")
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn('test error message', log_catcher.output[0])

    def test_console_error_object(self):
        with self.assertLogs(level='ERROR') as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error(TypeError('test error message'))"
                with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                    self.browser_js(url_path='about:blank', code=code)
            # second line must contains error message
            self.assertEqual(error_catcher.exception.args[0].splitlines()[-2:],
            ['TypeError: test error message', '    at <anonymous>:1:15'])
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn('TypeError: test error message\n    at <anonymous>:1:15', log_catcher.output[0])

    def test_console_log_object(self):
        logger = logging.getLogger('odoo')
        level = logger.level
        logger.setLevel(logging.INFO)
        self.addCleanup(logger.setLevel, level)

        with self.assertLogs() as log_catcher:
            code = "console.log({custom:{1:'test', 2:'a'}, value:1, description:'dummy'});console.log('test successful');"
            self.browser_js(url_path='about:blank', code=code)
        console_log_count = 0
        for log in log_catcher.output:
            if '.browser:' in log:
                text = log.split('.browser:', 1)[1]
                if text == 'test successful':
                    continue
                self.assertEqual(text, "Object(custom=Object, value=1, description='dummy')")
                console_log_count += 1
        self.assertEqual(console_log_count, 1)


@tagged('-at_install', 'post_install')
class TestChromeBrowser(HttpCase):
    def setUp(self):
        super().setUp()
        screencasts_dir = config['screencasts'] or config['screenshots']
        with patch.dict(config.options, {'screencasts': screencasts_dir, 'screenshots': config['screenshots']}):
            self.browser = ChromeBrowser(self)
        self.addCleanup(self.browser.stop)

    def test_screencasts(self):
        self.browser.start_screencast()
        self.browser.navigate_to('about:blank')
        self.browser._wait_ready()
        code = "setTimeout(() => console.log('test successful'), 2000); setInterval(() => document.body.innerText = (new Date()).getTime(), 100);"
        self.browser._wait_code_ok(code, 10)
        self.browser._save_screencast()
