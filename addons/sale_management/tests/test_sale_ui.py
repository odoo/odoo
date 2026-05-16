# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.tests.common import TestSaleCommon


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


@tagged('-at_install', 'post_install')
class TestSaleFlowTourPostInstall(TestSaleCommon, HttpCase):

    def test_basic_sale_flow_with_minimal_access_rights(self):
        """
        Test that a sale user with minimal access rights (own document only) can open both the
        list and form view, create and process a sale order and open the associated invoice.
        """
        sale_user = self.env['res.users'].create({
            'name': 'Super Sale Woman',
            'login': 'SuperSaleWoman',
            'group_ids': [Command.set([self.ref('sales_team.group_sale_salesman')])],
        })
        # create and confirm a sale order to populate the list view
        sale_order = self.env['sale.order'].with_user(sale_user.id).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })
        sale_order.action_confirm()
        self.start_tour('/odoo', 'test_basic_sale_flow_with_minimal_access_rights', login='SuperSaleWoman')
