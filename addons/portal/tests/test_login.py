# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.web.tests.test_login import TestWebLoginCommon


@tagged('-at_install', 'post_install')
class TestWebLoginPortal(TestWebLoginCommon):
    def test_web_login_external(self):
        res_post = self.login('portal_user', 'portal_user')
        # ensure we end up on the right page
        self.assertEqual(res_post.request.path_url, '/my')
