# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged
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
                console_log_count +=1
        self.assertEqual(console_log_count, 1)

    @patch.dict(config.options, {"dev_mode": []})
    def test_404_assets(self):
        IrAttachment = self.env['ir.attachment']
        # Ensure no assets exists
        IrAttachment.search([('url', '=like', '/web/assets/%')]).unlink()
        response = self.url_open('/NoSuchPage')
        self.assertEqual(response.status_code, 404, "Page should not exist")
        self.assertFalse(
            IrAttachment.search_count([('url', '=like', '/web/assets/%')]),
            "Assets should not have been generated because the transaction was rolled back"
            # Well, they should - but this is part of a compromise to avoid
            # being in the way of the read-only mode.
        )
        response = self.url_open('/')
        self.assertEqual(response.status_code, 200, "Page should exist")
        self.assertTrue(
            IrAttachment.search_count([('url', '=like', '/web/assets/%')]),
            "Assets should have been generated"
        )
