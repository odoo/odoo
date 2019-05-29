# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import Form, tagged

@tagged('post_install', '-at_install')
class TestStockValuation(AccountingTestCase):
    def setUp(self):
        super(TestStockValuation, self).setUp()
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product1 = self.env.ref('product.product_product_8')
        self.categ_id = self.product1.categ_id

        self.acc_payable = self.partner_id.property_account_payable_id.id
        self.acc_expense = self.categ_id.property_account_expense_categ_id.id
        self.acc_receivable = self.partner_id.property_account_receivable_id.id
        self.acc_sale = self.categ_id.property_account_income_categ_id.id
        self.acc_stock_in = self.categ_id.property_stock_account_input_categ_id.id
        self.acc_stock_out = self.categ_id.property_stock_account_output_categ_id.id

    def _dropship_product1(self):
        # enable the dropship and MTO route on the product
        dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        self.product1.write({'route_ids': [(6, 0, [dropshipping_route.id, mto_route.id])]})

        # add a vendor
        vendor1 = self.env['res.partner'].create({'name': 'vendor1'})
        seller1 = self.env['product.supplierinfo'].create({
            'name': vendor1.id,
            'price': 8,
        })
        self.product1.write({'seller_ids': [(6, 0, [seller1.id])]})

        # sell one unit of this product
        customer1 = self.env['res.partner'].create({'name': 'customer1'})
        self.sale_order1 = self.env['sale.order'].create({
            'partner_id': customer1.id,
            'partner_invoice_id': customer1.id,
            'partner_shipping_id': customer1.id,
            'order_line': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 1,
                'product_uom': self.product1.uom_id.id,
                'price_unit': 12,
            })],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.sale_order1.action_confirm()

        # confirm the purchase order
        self.purchase_order1 = self.env['purchase.order'].search([('group_id', '=', self.sale_order1.procurement_group_id.id)])
        self.purchase_order1.button_confirm()

        # validate the dropshipping picking
        self.assertEqual(len(self.sale_order1.picking_ids), 1)
        #self.assertEqual(self.sale_order1.picking_ids.move_lines._is_dropshipped(), True)
        wizard = self.sale_order1.picking_ids.button_validate()
        immediate_transfer = self.env[wizard['res_model']].browse(wizard['res_id'])
        immediate_transfer.process()
        self.assertEqual(self.sale_order1.picking_ids.state, 'done')

        # create the vendor bill
        move_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        move_form.partner_id = vendor1
        move_form.purchase_id = self.purchase_order1
        self.vendor_bill1 = move_form.save()
        self.vendor_bill1.post()

        # create the customer invoice
        self.customer_invoice1 = self.sale_order1._create_invoices()
        self.customer_invoice1.post()

        all_amls = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.move_lines.account_move_ids:
            all_amls |= self.sale_order1.picking_ids.move_lines.account_move_ids.line_ids
        return all_amls

    def _check_results(self, expected_aml, expected_aml_count, all_amls):
        # Construct a dict similar to `expected_aml` with `all_amls` in order to
        # compare them.
        result_aml = {}
        for aml in all_amls:
            account_id = aml.account_id.id
            if result_aml.get(account_id):
                debit = result_aml[account_id][0]
                credit = result_aml[account_id][1]
                result_aml[account_id] = (debit + aml.debit, credit + aml.credit)
            else:
                result_aml[account_id] = (aml.debit, aml.credit)

        self.assertEqual(len(all_amls), expected_aml_count)

        for k, v in expected_aml.items():
            self.assertEqual(result_aml[k], v)

    # -------------------------------------------------------------------------
    # Continental
    # -------------------------------------------------------------------------
    def test_dropship_standard_perpetual_continental_ordered(self):
        self.env.company.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_standard_perpetual_continental_delivered(self):
        self.env.company.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_fifo_perpetual_continental_ordered(self):
        self.env.company.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.proprty_cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_fifo_perpetual_continental_delivered(self):
        self.env.company.anglo_saxon_accounting = False

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    # -------------------------------------------------------------------------
    # Anglosaxon
    # -------------------------------------------------------------------------
    def test_dropship_standard_perpetual_anglosaxon_ordered(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (10.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
            self.acc_stock_in:   (8.0, 10.0),
            self.acc_stock_out:  (10.0, 10.0),
        }
        # Interim IN is not balanced because because there's a difference between the po line
        # price unit and the standard price. We could set a price difference account on the
        # category to compensate.

        self._check_results(expected_aml, 10, all_amls)

    def test_dropship_standard_perpetual_anglosaxon_delivered(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (10.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
            self.acc_stock_in:   (8.0, 10.0),
            self.acc_stock_out:  (10.0, 10.0),
        }
        # Interim IN is not balanced because because there's a difference between the po line
        # price unit and the standard price. We could set a price difference account on the
        # category to compensate.

        self._check_results(expected_aml, 10, all_amls)

    def test_dropship_fifo_perpetual_anglosaxon_ordered(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (10.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
            self.acc_stock_in:   (8.0, 8.0),
            self.acc_stock_out:  (8.0, 10.0),
        }

        self._check_results(expected_aml, 10, all_amls)

    def test_dropship_fifo_perpetual_anglosaxon_delivered(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
            self.acc_stock_in:   (8.0, 8.0),
            self.acc_stock_out:  (8.0, 8.0),
        }

        self._check_results(expected_aml, 10, all_amls)

    def test_dropship_standard_perpetual_anglosaxon_ordered_return(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        # return what we've done
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=self.sale_order1.picking_ids.ids, active_id=self.sale_order1.picking_ids.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pick.action_done()
        self.assertEqual(return_pick.move_lines._is_dropshipped_returned(), True)

        all_amls_return = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.mapped('move_lines.account_move_ids'):
            all_amls_return |= self.sale_order1.picking_ids.mapped('move_lines.account_move_ids.line_ids')

        # Two extra AML should have been created for the return
        expected_aml = {
            self.acc_stock_in:   (10.0, 0.0),
            self.acc_stock_out:  (0.0, 10.0),
        }

        self._check_results(expected_aml, 4, all_amls_return - all_amls)
