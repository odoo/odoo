# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import Form
from odoo import Command


class TestPurchaseRequisitionSale(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.client = cls.env['res.partner'].create({'name': 'Client'})
        cls.vendor_1 = cls.env['res.partner'].create({'name': 'Vendor 1'})
        cls.vendor_2 = cls.env['res.partner'].create({'name': 'Vendor 2'})

        cls.sub_service = cls.env['product.product'].create({
            'name': 'Subcontracted service',
            'type': 'service',
            'seller_ids': [Command.create({
                'partner_id': cls.vendor_1.id,
                'price': 10.0,
                'delay': 0,
            })],
            'service_to_purchase': True,
        })

    def test_01_purchase_requisition_services(self):
        """ Create an alternative RFQ for a RFQ automatically genrated from a sale order containing a service that
            has the "service_to_purchase" activated.
        """
        # Create a Sale Order for the subcontracted service
        sale_order = self.env['sale.order'].create({
            'partner_id': self.client.id,
            'order_line': [
                Command.create({
                    'product_id': self.sub_service.id,
                    'product_uom_qty': 5,
                })
            ]
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.purchase_order_count, 1, "A RFQ should be created, since `service_to_purchase` has been activated for this product")
        purchase_order = sale_order._get_purchase_orders()
        self.assertEqual(len(purchase_order), 1, "There should be only one Purchase Order linked to this Sale Order")

        # Create an alternative RFQ for another vendor
        action = purchase_order.action_create_alternative()
        alt_po_wizard = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard.partner_ids = self.vendor_2
        alt_po_wizard.copy_products = True
        alt_po_wizard = alt_po_wizard.save()
        alt_po_wizard.action_create_alternative()
        self.assertEqual(len(purchase_order.alternative_po_ids), 2, "Base PO should be linked with the alternative PO")

        # Check if newly created PO is correctly linked to the base Sale Order
        alt_po = purchase_order.alternative_po_ids.filtered(lambda po: po.id != purchase_order.id)
        linked_so = alt_po._get_sale_orders()
        self.assertEqual(len(linked_so), 1, "The Sale Order from the original Purchase Order should be linked")
        self.assertEqual(linked_so.id, sale_order.id, "The Sale Order linked to the alternative PO must be the same as the original one")
        self.assertEqual(sale_order.purchase_order_count, 2, "Both the original PO and the alternative one should be there")
