# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.agrolait = cls.env['res.partner'].create({'name': 'Agrolait', 'email': 'agro@lait.be'})

    def test_01_sale_tour(self):
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        self.start_tour("/odoo", 'sale_tour', login="admin")

    def test_04_portal_sale_signature_without_name_tour(self):
        """The goal of this test is to make sure the portal user can sign SO even witout a name."""
        self.agrolait.name = ""

        sales_order = self.env['sale.order'].sudo().create({
            'name': 'test SO',
            'partner_id': self.agrolait.id,
            'state': 'sent',
            'require_payment': False,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                })
            ]
        })
        action = sales_order.action_preview_sale_order()

        self.start_tour(action['url'], 'sale_signature_without_name', login="admin")
