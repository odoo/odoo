# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal


@tagged('post_install', '-at_install')
class TestWEventBoothExhibitor(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_register(self):
        module_event_booth_sale = self.env['ir.module.module']._get('event_booth_sale')
        if module_event_booth_sale.state == 'installed':
            # The flow of registration with payment is handled in a separate test.
            self.env.ref('event_booth.event_booth_category_premium').write({
                'price': 0.0,
            })
        self.start_tour('/event', 'webooth_exhibitor_register', login='admin')
