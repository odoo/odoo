# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import tools


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.env['blog.blog'].create({'name': 'Travel'})
        self.start_tour("/", 'blog', login='admin')
