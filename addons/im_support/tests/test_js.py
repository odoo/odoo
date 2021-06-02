# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class IMSupportSuite(odoo.tests.HttpCase):

    def test_im_support_js(self):
        self.phantom_js('/im_support/tests?mod=web&failfast', "", "", login='admin', timeout=180)
