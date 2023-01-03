# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.tests.common import HttpCase, new_test_user


class TestController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(cls.env, login='portal_user', groups='base.group_portal')
        cls.admin_user = new_test_user(cls.env, login='admin_user', groups='base.group_user,base.group_system')
        cls.headers = {"Content-Type": "application/json"}
        cls.pixel = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='

    def _build_payload(self, params=None):
        """
        Helper to properly build jsonrpc payload
        """
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": params or {},
        }

    def test_01_portal_attachment(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        payload = self._build_payload({'name': 'pixel', 'data': self.pixel, 'is_image': True, 'res_model': 'forum.post', 'res_id': 1})
        self.portal_user.karma = 30
        response = self.url_open('/web_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers, timeout=60000)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

    def test_02_admin_attachment(self):
        self.authenticate(self.admin_user.login, self.admin_user.login)
        payload = self._build_payload({"name": "pixel", "data": self.pixel, "is_image": True, "res_model": "forum.post"})
        response = self.url_open('/web_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

        attachment = self.env['ir.attachment'].create([{'name': 'test_pixel', 'public': True, 'res_id': False,
                                                        'mimetype': 'text/plain', 'res_model': 'forum.post',
                                                        'raw': self.pixel, 'website_id': 1}])
        domain = [('name', '=', 'test_pixel')]
        result = attachment.search(domain, limit=1)
        self.assertTrue(result, "No attachment fetched")
        self.assertEqual(result.id, attachment.id)
