# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestStockValuation(AccountingTestCase):
    def setUp(self):
        super(TestStockValuation, self).setUp()
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product1 = self.env.ref('product.product_product_8')

        self.acc_payable = self.env['account.account'].search([('name', '=', 'Account Payable')]).id
        self.acc_expense = self.env['account.account'].search([('name', '=', 'Expenses')]).id
        self.acc_receivable = self.env['account.account'].search([('name', '=', 'Account Receivable')]).id
        self.acc_sale = self.env['account.account'].search([('name', '=', 'Product Sales')]).id
        self.acc_stock_in = self.env['account.account'].search([('name', '=', 'Stock Interim Account (Received)')]).id
        self.acc_stock_out = self.env['account.account'].search([('name', '=', 'Stock Interim Account (Delivered)')]).id

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
        sale_order1 = self.env['sale.order'].create({
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
        sale_order1.action_confirm()

        # confirm the purchase order
        purchase_order1 = self.env['purchase.order'].search([('group_id', '=', sale_order1.procurement_group_id.id)])
        purchase_order1.button_confirm()

        # validate the dropshipping picking
        self.assertEqual(len(sale_order1.picking_ids), 1)
        self.assertEqual(sale_order1.picking_ids.move_lines._is_dropshipped(), True)
        wizard = sale_order1.picking_ids.button_validate()
        immediate_transfer = self.env[wizard['res_model']].browse(wizard['res_id'])
        immediate_transfer.process()
        self.assertEqual(sale_order1.picking_ids.state, 'done')

        # create the vendor bill
        vendor_bill1 = self.env['account.invoice'].create({
            'partner_id': vendor1.id,
            'purchase_id': purchase_order1.id,
            'account_id': vendor1.property_account_payable_id.id,
            'type': 'in_invoice',
        })
        vendor_bill1.purchase_order_change()
        vendor_bill1.action_invoice_open()

        # create the customer invoice
        customer_invoice1_id = sale_order1.action_invoice_create()
        customer_invoice1 = self.env['account.invoice'].browse(customer_invoice1_id)
        customer_invoice1.action_invoice_open()

        all_amls = vendor_bill1.move_id.line_ids + customer_invoice1.move_id.line_ids
        if sale_order1.picking_ids.move_lines.account_move_ids:
            all_amls |= sale_order1.picking_ids.move_lines.account_move_ids.line_ids
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
        self.env.user.company_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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
        self.env.user.company_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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
        self.env.user.company_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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
        self.env.user.company_id.anglo_saxon_accounting = False

        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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
        self.env.user.company_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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

        self._check_results(expected_aml, 8, all_amls)

    def test_dropship_standard_perpetual_anglosaxon_delivered(self):
        self.env.user.company_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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

        self._check_results(expected_aml, 8, all_amls)

    def test_dropship_fifo_perpetual_anglosaxon_ordered(self):
        self.env.user.company_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        all_amls = self._dropship_product1()

        expected_aml = {
            self.acc_payable:    (0.0, 8.0),
            self.acc_expense:    (8.0, 0.0),
            self.acc_receivable: (12.0, 0.0),
            self.acc_sale:       (0.0, 12.0),
            self.acc_stock_in:   (8.0, 8.0),
            self.acc_stock_out:  (8.0, 8.0),
        }

        self._check_results(expected_aml, 8, all_amls)

    def test_dropship_fifo_perpetual_anglosaxon_delivered(self):
        self.env.user.company_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.valuation = 'real_time'
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

        self._check_results(expected_aml, 8, all_amls)

