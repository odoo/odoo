# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install')
class TestPurchaseFlowTourPostInstall(AccountTestInvoicingCommon, HttpCase):

    def test_basic_purchase_flow_with_minimal_access_rights(self):
        """
        Test that a purchase user with minimal access rights can open both the list and form view,
        create and process a purchase order, upload and open the associated vendor bill.
        """
        purchase_user = self.env['res.users'].create({
            'name': 'Super Purchase Woman',
            'login': 'SuperPurchaseWoman',
            'group_ids': [Command.set([self.ref('purchase.group_purchase_user')])],
        })
        # create and confirm a PO to populate the list view
        purchase_order = self.env['purchase.order'].with_user(purchase_user.id).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })
        purchase_order.button_approve()
        self.start_tour('/odoo', 'test_basic_purchase_flow_with_minimal_access_rights', login='SuperPurchaseWoman')
