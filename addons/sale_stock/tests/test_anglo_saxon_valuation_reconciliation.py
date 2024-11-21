# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import Form, tagged


class TestValuationReconciliationCommon(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

        # Set the invoice_policy to delivery to have an accurate COGS entry.
        cls.test_product_delivery.invoice_policy = 'delivery'

    def _create_sale(self, product, date, quantity=1.0):
        rslt = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': 66.0,
                })],
            'date_order': date,
        })
        rslt.action_confirm()
        return rslt

    def _create_invoice_for_so(self, sale_order, product, date, quantity=1.0):
        rslt = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'move_type': 'out_invoice',
            'invoice_date': date,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': 66.0,
                'quantity': quantity,
                'discount': 0.0,
                'product_uom_id': product.uom_id.id,
                'product_id': product.id,
                'sale_line_ids': [(6, 0, sale_order.order_line.ids)],
            })],
        })

        sale_order.invoice_ids += rslt
        return rslt

    def _set_initial_stock_for_product(self, product):
        move1 = self.env['stock.move'].create({
            'name': 'Initial stock',
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 11,
            'price_unit': 13,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({'quantity': 11, 'picked': True})
        move1._action_done()


@tagged('post_install', '-at_install')
class TestValuationReconciliation(TestValuationReconciliationCommon):
    def test_shipment_invoice(self):
        """ Tests the case into which we send the goods to the customer before
        making the invoice
        """
        test_product = self.test_product_delivery
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product, '2108-01-01')
        self._process_pickings(sale_order.picking_ids)

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-12')
        invoice.action_post()
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking, operation='sale')

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then send
        the goods to our customer.
        """
        test_product = self.test_product_delivery
        #since the invoice come first, the COGS will use the standard price on product
        self.test_product_delivery.standard_price = 13
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product, '2018-01-01')

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-03')
        invoice.action_post()

        self._process_pickings(sale_order.picking_ids)

        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking, operation='sale')

        #return the goods and refund the invoice
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_ids.write({'quantity': 1, 'picked': True})
        return_pick._action_done()
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'journal_id': invoice.journal_id.id,
        })
        new_invoice = self.env['account.move'].browse(refund_invoice_wiz.modify_moves()['res_id'])
        self.assertEqual(invoice.payment_state, 'reversed', "Invoice should be in 'reversed' state.")
        self.assertEqual(invoice.reversal_move_ids.payment_state, 'paid', "Refund should be in 'paid' state.")
        self.assertEqual(new_invoice.state, 'draft', "New invoice should be in 'draft' state.")
        self.check_reconciliation(invoice.reversal_move_ids, return_pick, operation='sale')

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we deliver part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.test_product_delivery
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product, '2018-01-01', quantity=5)

        self._process_pickings(sale_order.picking_ids, quantity=2.0)
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)], order="id asc", limit=1)

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-03', quantity=3)
        invoice.action_post()
        self.check_reconciliation(invoice, picking, full_reconcile=False, operation='sale')

        invoice2 = self._create_invoice_for_so(sale_order, test_product, '2018-03-12', quantity=2)
        invoice2.action_post()
        self.check_reconciliation(invoice2, picking, full_reconcile=False, operation='sale')

        self._process_pickings(sale_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)], order='id desc', limit=1)
        self.check_reconciliation(invoice2, picking, operation='sale')

    def test_fifo_multiple_products(self):
        """ Test Automatic Inventory Valuation with FIFO costs method, 3 products,
            2,3,4 out svls and 2 in moves by product. This tests a more complex use case with anglo-saxon accounting.
        """
        wh = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ])
        stock_loc = wh.lot_stock_id
        in_type = wh.in_type_id
        product_1, product_2, = tuple(self.env['product.product'].create([{
            'name': f'P{i}',
            'list_price': 10 * i,
            'standard_price': 10 * i,
            'is_storable': True,
        } for i in range(1, 3)]))
        product_1.categ_id.property_valuation = 'real_time'
        product_1.categ_id.property_cost_method = 'fifo'
        # give another output account to product_2
        categ_2 = product_1.categ_id.copy()
        account_2 = categ_2.property_stock_account_output_categ_id.copy()
        categ_2.property_stock_account_output_categ_id = account_2
        product_2.categ_id = categ_2
        # Create out_svls
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 2,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': 10.0,
                }) for product in 2 * [product_1] + [product_2]],
            'date_order': '2021-01-01',
        })
        so.action_confirm()
        so.picking_ids.move_ids.quantity = 2
        so.picking_ids.move_ids.picked = True
        so.picking_ids._action_done()
        self.assertEqual(so.picking_ids.state, 'done')
        inv = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'move_type': 'out_invoice',
            'invoice_date': '2021-01-10',
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': 10.0,
                'quantity': 2,
                'discount': 0.0,
                'product_uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'sale_line_ids': [(6, 0, line.ids)],
            }) for line in so.order_line],
        })

        so.invoice_ids += inv
        inv.action_post()
        # Create in_moves for P1/P2 such that the first move compensates the out_svls
        in_moves = self.env['stock.move'].create([{
            'name': 'in %s units @ %s per unit' % (str(quantity), str(product.standard_price)),
            'description_picking': '%s-%s' % (str(quantity), str(product)),  # to not merge the moves
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock_loc.id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': quantity,
            'price_unit': product.standard_price + 1,
            'picking_type_id': in_type.id,
        } for product, quantity in zip(
            [product_1, product_2],
            [2.0, 2.0]
        )])
        in_moves._action_confirm()
        for move in in_moves:
            move.quantity = move.product_uom_qty
            move.picked = True
        in_moves._action_done()

        self.assertEqual(product_1.value_svl, -20)
        self.assertEqual(product_2.value_svl, 0)
        # Check that the correct number of amls have been created and posted
        input_aml = self.env['account.move.line'].search([
            ('account_id', '=', product_1.categ_id.property_stock_account_input_categ_id.id),
        ], order='date, id')
        output1_aml = self.env['account.move.line'].search([
            ('account_id', '=', product_1.categ_id.property_stock_account_output_categ_id.id),
        ], order='date, id')
        output2_aml = self.env['account.move.line'].search([
            ('account_id', '=', product_2.categ_id.property_stock_account_output_categ_id.id),
        ], order='date, id')
        valo_aml = self.env['account.move.line'].search([
            ('account_id', '=', product_1.categ_id.property_stock_valuation_account_id.id),
        ], order='date, id')
        self.assertEqual(len(input_aml), 2)
        self.assertEqual(len(output1_aml), 6)
        self.assertEqual(len(output2_aml), 4)
        self.assertEqual(len(valo_aml), 7)
        # All amls should be reconciled
        self.assertTrue(all(aml.reconciled for aml in output1_aml + output2_aml))
