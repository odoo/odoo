# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestStockValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.company_data['default_warehouse'].lot_stock_id
        cls.partner_id = cls.env['res.partner'].create({'name': 'My Test Partner'})
        cls.product1 = cls.env['product.product'].create({
            'name': 'Large Desk',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'taxes_id': [(6, 0, [])],
        })

    def _dropship_product1(self):
        # enable the dropship and MTO route on the product
        dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        self.product1.write({'route_ids': [(6, 0, [dropshipping_route.id, mto_route.id])]})

        # add a vendor
        vendor1 = self.env['res.partner'].create({'name': 'vendor1'})
        seller1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
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
                'tax_id': [(6, 0, [])],
            })],
            'picking_policy': 'direct',
        })
        self.sale_order1.action_confirm()

        # confirm the purchase order
        self.purchase_order1 = self.env['purchase.order'].search([('group_id', '=', self.sale_order1.procurement_group_id.id)])
        self.purchase_order1.button_confirm()

        # validate the dropshipping picking
        self.assertEqual(len(self.sale_order1.picking_ids), 1)
        self.sale_order1.picking_ids.button_validate()
        self.assertEqual(self.sale_order1.picking_ids.state, 'done')

        # create the vendor bill
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = vendor1
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-self.purchase_order1.id)
        move_form.invoice_date = move_form.date
        for i in range(len(self.purchase_order1.order_line)):
            with move_form.invoice_line_ids.edit(i) as line_form:
                line_form.tax_ids.clear()
        self.vendor_bill1 = move_form.save()
        self.vendor_bill1.action_post()

        # create the customer invoice
        self.customer_invoice1 = self.sale_order1._create_invoices()
        self.customer_invoice1.action_post()

        all_amls = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.move_ids.account_move_ids:
            all_amls |= self.sale_order1.picking_ids.move_ids.account_move_ids.line_ids
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_fifo_perpetual_continental_ordered(self):
        self.env.company.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (10.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
            self.company_data['default_account_stock_in'].id:       (8.0, 10.0),
            self.company_data['default_account_stock_out'].id:      (10.0, 10.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (10.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
            self.company_data['default_account_stock_in'].id:       (8.0, 10.0),
            self.company_data['default_account_stock_out'].id:      (10.0, 10.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
            self.company_data['default_account_stock_in'].id:       (8.0, 8.0),
            self.company_data['default_account_stock_out'].id:      (8.0, 8.0),
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
            self.company_data['default_account_payable'].id:        (0.0, 8.0),
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
            self.company_data['default_account_stock_in'].id:       (8.0, 8.0),
            self.company_data['default_account_stock_out'].id:      (8.0, 8.0),
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
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()
        self.assertEqual(return_pick.move_ids._is_dropshipped_returned(), True)

        all_amls_return = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.mapped('move_ids.account_move_ids'):
            all_amls_return |= self.sale_order1.picking_ids.mapped('move_ids.account_move_ids.line_ids')

        # Two extra AML should have been created for the return
        expected_aml = {
            self.company_data['default_account_stock_in'].id:       (10.0, 0.0),
            self.company_data['default_account_stock_out'].id:      (0.0, 10.0),
        }

        self._check_results(expected_aml, 4, all_amls_return - all_amls)

    def test_dropship_fifo_return(self):
        """Test the return of a dropship order with a product set to FIFO costing
        method. The unit price is correctly computed on the return picking svl.
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        self._dropship_product1()
        self.assertTrue(8 in self.purchase_order1.picking_ids.move_ids.stock_valuation_layer_ids.mapped('value'))
        self.assertTrue(-8 in self.purchase_order1.picking_ids.move_ids.stock_valuation_layer_ids.mapped('value'))

        # return what we've done
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=self.sale_order1.picking_ids.ids, active_id=self.sale_order1.picking_ids.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()

        self.assertTrue(8 in return_pick.move_ids.stock_valuation_layer_ids.mapped('value'))
        self.assertTrue(-8 in return_pick.move_ids.stock_valuation_layer_ids.mapped('value'))

        # return again to have a new dropship picking from a dropship return
        stock_return_picking_form_2 = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_pick.ids, active_id=return_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking_2 = stock_return_picking_form_2.save()
        stock_return_picking_2.product_return_moves.quantity = 1.0
        stock_return_picking_action_2 = stock_return_picking_2.action_create_returns()
        return_pick_2 = self.env['stock.picking'].browse(stock_return_picking_action_2['res_id'])
        return_pick_2.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick_2.move_ids[0].picked = True
        return_pick_2._action_done()

        self.assertTrue(8 in return_pick_2.move_ids.stock_valuation_layer_ids.mapped('value'))
        self.assertTrue(-8 in return_pick_2.move_ids.stock_valuation_layer_ids.mapped('value'))
