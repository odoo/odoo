# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, HttpCase):

    def test_01_sale_tour(self):
        self.env['res.partner'].create({'name': 'Agrolait', 'email': 'agro@lait.be'})
        self.start_tour("/odoo", 'sale_tour', login="admin")

    def test_04_portal_sale_signature_without_name_tour(self):
        """The goal of this test is to make sure the portal user can sign SO even witout a name."""

        portal_user_partner = self.env['res.partner'].create({'name': 'Agrolait', 'email': 'agro@lait.be'})
        # create a SO to be signed
        portal_user_partner.name = ""
        sales_order = self.env['sale.order'].create({
            'name': 'test SO',
            'partner_id': portal_user_partner.id,
            'state': 'sent',
            'require_payment': False,
        })
        self.env['sale.order.line'].create({
            'order_id': sales_order.id,
            'product_id': self.env['product.product'].create({'name': 'A product'}).id,
        })

        action = sales_order.action_preview_sale_order()

        self.start_tour(action['url'], 'sale_signature_without_name', login="admin")
