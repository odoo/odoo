# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class StockMoveInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.ProductProduct = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.AccountJournal = cls.env['account.journal']

        cls.partner_18 = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.pricelist_id = cls.env.ref('product.list0')
        cls.product_11 = cls.env['product.product'].create({'name': 'A product to deliver'})
        cls.product_cable_management_box = cls.env['product.product'].create({
            'name': 'Another product to deliver',
            'weight': 1.0,
            'invoice_policy': 'order',
        })
        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_delivery_normal = cls.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.normal_delivery = cls.env['delivery.carrier'].create({
            'name': 'Normal Delivery Charges',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery_normal.id,
        })

    def test_01_delivery_stock_move(self):
        # Test if the stored fields of stock moves are computed with invoice before delivery flow
        self.sale_prepaid = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist_id.id,
            'order_line': [(0, 0, {
                'name': 'Cable Management Box',
                'product_id': self.product_cable_management_box.id,
                'product_uom_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_prepaid.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I confirm the SO.
        self.sale_prepaid.action_confirm()
        self.sale_prepaid._create_invoices()

        # I check that the invoice was created
        self.assertEqual(len(self.sale_prepaid.invoice_ids), 1, "Invoice not created.")

        # I confirm the invoice

        self.invoice = self.sale_prepaid.invoice_ids
        self.invoice.action_post()

        # I pay the invoice.
        self.journal = self.AccountJournal.search([('type', '=', 'cash'), ('company_id', '=', self.sale_prepaid.company_id.id)], limit=1)

        register_payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.invoice.ids).create({
            'journal_id': self.journal.id,
        })
        register_payments._create_payments()

        # Check the SO after paying the invoice
        self.assertNotEqual(self.sale_prepaid.invoice_count, 0, 'order not invoiced')
        self.assertTrue(self.sale_prepaid.invoice_status == 'invoiced', 'order is not invoiced')
        self.assertEqual(len(self.sale_prepaid.picking_ids), 1, 'pickings not generated')

        # Check the stock moves
        moves = self.sale_prepaid.picking_ids.move_ids
        self.assertEqual(moves[0].product_qty, 2, 'wrong product_qty')
        self.assertEqual(moves[0].weight, 2.0, 'wrong move weight')

        # Ship
        moves.move_line_ids.write({'qty_done': 2})
        self.picking = self.sale_prepaid.picking_ids._action_done()
        self.assertEqual(moves[0].move_line_ids.sale_price, 1725.0, 'wrong shipping value')

    def test_02_delivery_stock_move(self):
        # Test if SN product shipment line has the correct amount
        self.product_cable_management_box.write({
            'tracking': 'serial'
        })

        serial_numbers = self.env['stock.lot'].create([{
            'name': str(x),
            'product_id': self.product_cable_management_box.id,
            'company_id': self.env.company.id,
        } for x in range(5)])

        self.sale_prepaid = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist_id.id,
            'order_line': [(0, 0, {
                'name': 'Cable Management Box',
                'product_id': self.product_cable_management_box.id,
                'product_uom_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_prepaid.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I confirm the SO.
        self.sale_prepaid.action_confirm()
        moves = self.sale_prepaid.picking_ids.move_ids
        # Ship
        for ml, lot in zip(moves.move_line_ids, serial_numbers):
            ml.write({'qty_done': 1, 'lot_id': lot.id})
        self.picking = self.sale_prepaid.picking_ids._action_done()
        self.assertEqual(moves[0].move_line_ids[0].sale_price, 862.5, 'wrong shipping value')

    def test_03_invoiced_status(self):
        super_product = self.env['product.product'].create({
            'name': 'Super Product',
            'invoice_policy': 'delivery',
        })
        great_product = self.env['product.product'].create({
            'name': 'Great Product',
            'invoice_policy': 'delivery',
        })

        so = self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': super_product.name, 'product_id': super_product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
                (0, 0, {'name': great_product.name, 'product_id': great_product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
            ]
        })
        # Confirm the SO
        so.action_confirm()

        # Deliver one product and create a backorder
        self.assertEqual(sum([line.quantity_done for line in so.picking_ids.move_ids]), 0)
        so.picking_ids.move_ids[0].quantity_done = 1
        backorder_wizard_dict = so.picking_ids.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(sum([line.quantity_done for line in so.picking_ids.move_ids]), 1)

        # Invoice the delivered product
        invoice = so._create_invoices()
        invoice.action_post()
        self.assertEqual(so.invoice_status, 'no')

        # Add delivery fee
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.normal_delivery.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        self.assertEqual(so.invoice_status, 'no', 'The status should still be "Nothing To Invoice"')

    def test_delivery_carrier_from_confirmed_so(self):
        """Test if adding shipping method in sale order after confirmation
           will add it in pickings too"""

        sale_order = self.SaleOrder.create({
            "partner_id": self.partner_18.id,
            "partner_invoice_id": self.partner_18.id,
            "partner_shipping_id": self.partner_18.id,
            "order_line": [(0, 0, {
                "name": "Cable Management Box",
                "product_id": self.product_cable_management_box.id,
                "product_uom_qty": 2,
                "product_uom": self.product_uom_unit.id,
                "price_unit": 750.00,
            })],
        })

        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.quantity_done = 2
        sale_order.picking_ids.button_validate()

        # Return picking
        return_form = Form(self.env["stock.return.picking"].with_context(active_id=sale_order.picking_ids.id, active_model="stock.picking"))
        return_wizard = return_form.save()
        action = return_wizard.create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])

        # add new product so new picking is created
        sale_order.write({
            "order_line": [(0, 0, {
                "name": "Another product to deliver",
                "product_id": self.product_11.id,
                "product_uom_qty": 2,
                "product_uom": self.product_uom_unit.id,
                "price_unit": 750.00,
            })],
        })

        # Add delivery cost in Sales order
        delivery_wizard = Form(self.env["choose.delivery.carrier"].with_context({
            "default_order_id": sale_order.id,
            "default_carrier_id": self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # Check the carrier in picking after confirm sale order
        delivery_for_product_11 = sale_order.picking_ids.filtered(lambda p: self.product_11 in p.move_ids.product_id)
        self.assertEqual(delivery_for_product_11.carrier_id, self.normal_delivery, "The shipping method should be set in pending deliveries.")

        done_delivery = sale_order.picking_ids.filtered(lambda p: p.state == "done")
        self.assertFalse(done_delivery.carrier_id.id, "The shipping method should not be set in done deliveries.")
        self.assertFalse(return_picking.carrier_id.id, "The shipping method should not set in return pickings")
