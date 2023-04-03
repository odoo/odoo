# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event_sale.tests.test_frontend_common import TestFrontendCommon
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestFrontendBuyTickets(TestFrontendCommon):

    def test_admin(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        # Seen that:
        # - this test relies on demo data that are entirely in USD (pricelists)
        # - that main demo company is gelocated in US
        # - that this test awaits for hardcoded USDs amount
        # we have to force company currency as USDs only for this test
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.ref('base.main_company').id])
        self.env['product.pricelist'].create({'name': "Public Pricelist"})

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/", 'event_buy_tickets', login="admin")

    def test_demo(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        #  Ensure the use of USD (company currency)
        self.env['product.pricelist'].create({'name': "Public Pricelist"})

        self.start_tour("/", 'event_buy_tickets', login="demo")

    def test_buy_last_ticket(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/", 'event_buy_last_ticket')

    def test_pricelists_different_currencies(self):
        self.start_tour("/", 'event_sale_pricelists_different_currencies', login='admin')
    # TO DO - add public test with new address when convert to web.tour format.
