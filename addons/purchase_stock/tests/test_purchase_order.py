# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrder(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.product_id_1 = cls.env['product.product'].create({'name': 'Large Desk', 'purchase_method': 'purchase'})
        cls.product_id_2 = cls.env['product.product'].create({'name': 'Conference Chair', 'purchase_method': 'purchase'})

        cls.po_vals = {
            'partner_id': cls.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': cls.product_id_1.name,
                    'product_id': cls.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': cls.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().replace(hour=9).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
                (0, 0, {
                    'name': cls.product_id_2.name,
                    'product_id': cls.product_id_2.id,
                    'product_qty': 5.0,
                    'product_uom': cls.product_id_2.uom_po_id.id,
                    'price_unit': 250.0,
                    'date_planned': datetime.today().replace(hour=9).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }

    def test_00_purchase_order_flow(self):
        # Ensure product_id_2 doesn't have res_partner_1 as supplier
        if self.partner_a in self.product_id_2.seller_ids.mapped('name'):
            id_to_remove = self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a).ids[0] if self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a) else False
            if id_to_remove:
                self.product_id_2.write({
                    'seller_ids': [(2, id_to_remove, False)],
                })
        self.assertFalse(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a), 'Purchase: the partner should not be in the list of the product suppliers')

        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.invoice_status, 'no', 'Purchase: PO invoice_status should be "Not purchased"')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        self.assertTrue(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a), 'Purchase: the partner should be in the list of the product suppliers')

        seller = self.product_id_2._select_seller(partner_id=self.partner_a, quantity=2.0, date=self.po.date_planned, uom_id=self.product_id_2.uom_po_id)
        price_unit = seller.price if seller else 0.0
        if price_unit and seller and self.po.currency_id and seller.currency_id != self.po.currency_id:
            price_unit = seller.currency_id._convert(price_unit, self.po.currency_id, self.po.company_id, self.po.date_order)
        self.assertEqual(price_unit, 250.0, 'Purchase: the price of the product for the supplier should be 250.0.')

        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

    def test_02_po_return(self):
        """
        Test a PO with a product on Incoming shipment. Validate the PO, then do a return
        of the picking with Refund.
        """
        # Draft purchase order created
        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        # Confirm the purchase order
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase')
        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        #After Receiving all products create vendor bill.
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()
        self.invoice.action_post()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

        # Check quantity received
        received_qty = sum(pol.qty_received for pol in self.po.order_line)
        self.assertEqual(received_qty, 10.0, 'Purchase: Received quantity should be 10.0 instead of %s after validating incoming shipment' % received_qty)

        # Create return picking
        pick = self.po.picking_ids
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick.ids, active_id=pick.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({'quantity': 2.0, 'to_refund': True})  # Return only 2
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.move_line_ids.write({'qty_done': 2})

        return_pick.button_validate()

        # Check Received quantity
        self.assertEqual(self.po.order_line[0].qty_received, 3.0, 'Purchase: delivered quantity should be 3.0 instead of "%s" after picking return' % self.po.order_line[0].qty_received)
        #Create vendor bill for refund qty
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        self.invoice = move_form.save()
        self.invoice.action_post()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [3.0, 3.0], 'Purchase: Billed quantity should be 3.0')

    def test_03_po_return_and_modify(self):
        """Change the picking code of the delivery to internal. Make a PO for 10 units, go to the
        picking and return 5, edit the PO line to 15 units.
        The purpose of the test is to check the consistencies across the received quantities and the
        procurement quantities.
        """
        # Change the code of the picking type delivery
        self.env['stock.picking.type'].search([('code', '=', 'outgoing')]).write({'code': 'internal'})

        # Sell and deliver 10 units
        item1 = self.product_id_1
        uom_unit = self.env.ref('uom.product_uom_unit')
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_qty': 10,
                    'product_uom': uom_unit.id,
                    'price_unit': 123.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking = po1.picking_ids
        wiz_act = picking.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # Return 5 units
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking.ids,
            active_id=picking.ids[0],
            active_model='stock.picking'
        ))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 5,
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        wiz_act = return_pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        self.assertEqual(po1.order_line.qty_received, 5)

        # Deliver 15 instead of 10.
        po1.write({
            'order_line': [
                (1, po1.order_line[0].id, {'product_qty': 15}),
            ]
        })

        # A new move of 10 unit (15 - 5 units)
        self.assertEqual(po1.order_line.qty_received, 5)
        self.assertEqual(po1.picking_ids[-1].move_lines.product_qty, 10)

    def test_04_update_date_planned(self):
        today = datetime.today().replace(hour=9, microsecond=0)
        tomorrow = datetime.today().replace(hour=9, microsecond=0) + timedelta(days=1)
        po = self.env['purchase.order'].create(self.po_vals)
        po.button_confirm()

        # update first line
        po._update_date_planned_for_lines([(po.order_line[0], tomorrow)])
        self.assertEqual(po.order_line[0].date_planned, tomorrow)
        activity = self.env['mail.activity'].search([
            ('summary', '=', 'Date Updated'),
            ('res_model_id', '=', 'purchase.order'),
            ('res_id', '=', po.id),
        ])
        self.assertTrue(activity)
        self.assertIn(
            '<p> partner_a modified receipt dates for the following products:</p><p> \xa0 - Large Desk from %s to %s </p><p>Those dates have been updated accordingly on the receipt %s.</p>' % (today.date(), tomorrow.date(), po.picking_ids.name),
            activity.note,
        )

        # receive products
        wiz_act = po.picking_ids.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # update second line
        old_date = po.order_line[1].date_planned
        po._update_date_planned_for_lines([(po.order_line[1], tomorrow)])
        self.assertEqual(po.order_line[1].date_planned, old_date)
        self.assertIn(
            '<p> partner_a modified receipt dates for the following products:</p><p> \xa0 - Large Desk from %s to %s </p><p> \xa0 - Conference Chair from %s to %s </p><p>Those dates couldn’t be modified accordingly on the receipt %s which had already been validated.</p>' % (today.date(), tomorrow.date(), today.date(), tomorrow.date(), po.picking_ids.name),
            activity.note,
        )

    def test_05_multi_company(self):
        company_a = self.env.user.company_id
        company_b = self.env['res.company'].create({
            "name": "Test Company",
            "currency_id": self.env['res.currency'].with_context(active_test=False).search([
                ('id', '!=', company_a.currency_id.id),
            ], limit=1).id
        })
        self.env.user.write({
            'company_id': company_b.id,
            'company_ids': [(4, company_b.id), (4, company_a.id)],
        })
        po = self.env['purchase.order'].create(dict(company_id=company_a.id, partner_id=self.partner_a.id))

        self.assertEqual(po.company_id, company_a)
        self.assertEqual(po.picking_type_id.warehouse_id.company_id, company_a)
        self.assertEqual(po.currency_id, po.company_id.currency_id)
