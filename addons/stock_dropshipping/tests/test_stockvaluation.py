# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


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

    def _dropship_product1(self, bill_price=None):
        # enable the dropship route on the product
        dropshipping_route = self.quick_ref('stock_dropshipping.route_drop_shipping')
        self.product1.write({'route_ids': [(6, 0, [dropshipping_route.id])]})

        # add a vendor
        vendor1 = self.env['res.partner'].create({'name': 'vendor1'})
        self.product1.write({
            'seller_ids': [
                Command.create({
                    'partner_id': vendor1.id,
                    'price': 8,
                })
            ]
        })

        # sell one unit of this product
        self.sale_order1 = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product1.id,
                    'price_unit': 12,
                    'tax_ids': [Command.set([])],
                })
            ],
            'picking_policy': 'direct',
        })
        self.sale_order1.action_confirm()

        # confirm the purchase order
        self.purchase_order1 = self.env['purchase.order'].search([('reference_ids', '=', self.sale_order1.stock_reference_ids.id)])
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
                if bill_price:
                    line_form.price_unit = bill_price
        self.vendor_bill1 = move_form.save()
        self.vendor_bill1.action_post()

        # create the customer invoice
        self.customer_invoice1 = self.sale_order1._create_invoices()
        self.customer_invoice1.action_post()

        all_amls = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.move_ids.account_move_id:
            all_amls |= self.sale_order1.picking_ids.move_ids.account_move_id.line_ids
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
            self.company_data['default_account_expense'].id:        (8.0, 0.0),
            self.company_data['default_account_receivable'].id:     (12.0, 0.0),
            self.company_data['default_account_revenue'].id:        (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_standard_perpetual_anglosaxon_delivered(self):
        self.env.company.anglo_saxon_accounting = True
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
        }

        self._check_results(expected_aml, 4, all_amls)

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
        }
        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_bill_standard_price_update(self):
        """ Test that the price of the product is updated when the bill has a different
        price than the Purchase order
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self._dropship_product1(bill_price=15)
        self.assertEqual(self.product1.standard_price, 15)

    def test_dropship_return_to_internal_location_is_valued(self):
        """Returning a dropshipped delivery into the company's own stock, instead
        of back to the vendor, brings the goods into inventory. The outgoing
        dropship never enters own stock and stays unvalued, but the returned move
        lands in a stock location: it is a valued incoming move, so the stock
        valuation account is debited when the period is closed.
        """
        self.env.user.group_ids |= self.env.ref('stock.group_stock_multi_locations')
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'

        self._dropship_product1()

        # the outgoing dropship never enters the company's stock: unvalued
        self.assertRecordValues(self.product1, [{'total_value': 0.0, 'qty_available': 0.0}])

        # return the delivery into an internal stock location, not to the vendor
        return_picking = Form(self.env['stock.return.picking'].with_context(
            active_ids=self.sale_order1.picking_ids.ids,
            active_id=self.sale_order1.picking_ids.ids[0],
            active_model='stock.picking')).save()
        return_picking.product_return_moves.quantity = 1.0
        return_action = return_picking.action_create_returns()
        return_picking = self.env['stock.picking'].browse(return_action['res_id'])
        return_picking.location_dest_id = self.stock_location
        return_picking.move_ids.move_line_ids.quantity = 1.0
        return_picking.move_ids.picked = True
        return_picking._action_done()

        # landing in a stock location, the return is a valued incoming move
        return_move = return_picking.move_ids
        self.assertFalse(return_move._is_dropshipped_returned())
        self.assertRecordValues(return_move, [{'is_in': True, 'is_valued': True}])
        self.assertRecordValues(self.product1, [{'total_value': 10.0, 'qty_available': 1.0}])

        # close the period to debit the stock valuation account for the goods
        # brought back into inventory
        closing_move = self.env['account.move'].browse(
            self.env.company.action_close_stock_valuation(auto_post=True)['res_id'])
        stock_valuation_account = self.company_data['default_account_stock_valuation']
        valuation_aml = closing_move.line_ids.filtered(
            lambda line: line.account_id == stock_valuation_account)
        self.assertRecordValues(valuation_aml, [{'debit': 10.0, 'credit': 0.0}])
