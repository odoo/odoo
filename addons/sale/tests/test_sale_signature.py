# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleSignature(HttpCaseWithUserPortal):
    def test_01_portal_sale_signature_tour(self):
        """The goal of this test is to make sure the portal user can sign SO."""

        self.env.company.portal_confirmation_sign = True
        self.env.company.portal_confirmation_pay = False

        SaleOrder = self.env["sale.order"]

        if "sale_order_template_id" in SaleOrder._fields.keys():
            # With sale_quotation_builder (and sale_management) module
            # A default sale order template is added for each company
            # In this case, the require_payment and require_signature field values
            # come from the template, enforcing the company defaults isn't enough
            # we also need to enforce the defaults on the template.
            default_template_id = SaleOrder.default_get(["sale_order_template_id"]).get("sale_order_template_id")
            if default_template_id:
                self.env["sale.order.template"].browse(default_template_id).write({
                    "require_payment": False,
                    "require_signature": True,
                })

        # create a SO to be signed
        sales_order = SaleOrder.create({
            'name': 'test SO',
            'partner_id': self.partner_portal.id,
            'state': 'sent',
            'order_line': [(0, False, {
                'product_id': self.env['product.product'].create({'name': 'A product'}).id,
            })],
        })

        self.assertFalse(sales_order.require_payment)
        self.assertTrue(sales_order.require_signature)

        # must be sent to the user so he can see it
        email_act = sales_order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        sales_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

        self.start_tour("/", 'sale_signature', login="portal")
