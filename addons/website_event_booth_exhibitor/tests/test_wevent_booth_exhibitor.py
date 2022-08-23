# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWEventBoothExhibitorCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_register(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer acquirer is not installed")

        transfer_acquirer = self.env.ref('payment.payment_acquirer_transfer')
        transfer_acquirer.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_acquirer._transfer_ensure_pending_msg_is_set()

        self.browser_js(
            '/event',
            'odoo.__DEBUG__.services["web_tour.tour"].run("webooth_exhibitor_register")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.webooth_exhibitor_register.ready',
            login='admin'
        )
