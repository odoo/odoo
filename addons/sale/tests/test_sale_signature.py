# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSaleSignature(odoo.tests.HttpCase):
    def test_01_portal_sale_signature_tour(self):
        """The goal of this test is to make sure the portal user can sign SO."""

        portal_user = self.env.ref('base.partner_demo_portal')
        # create a SO to be signed
        sales_order = self.env['sale.order'].create({
            'name': 'test SO',
            'partner_id': portal_user.id,
            'state': 'sent',
        })
        self.env['sale.order.line'].create({
            'order_id': sales_order.id,
            'product_id': self.env.ref('product.product_product_6').id,
        })

        # must be sent to the user so he can see it
        sales_order.force_quotation_send()

        self.browser_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('sale_signature')", "odoo.__DEBUG__.services['web_tour.tour'].tours.sale_signature.ready", login="portal")
