# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


class TestStockValuationLC(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationLC, cls).setUpClass()
        cls.productlc1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'service',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.product1.write({
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.productlc1.write({
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })
        cls.payable_account = cls.env['account.account'].create({
            'name': 'payable',
            'code': 'payable',
            'user_type_id': cls.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })

    def _get_stock_input_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_input_account.id),
        ], order='id')

    def _get_stock_output_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_output_account.id),
        ], order='id')

    def _get_stock_valuation_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_valuation_account.id),
        ], order='id')

    def _get_payable_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.payable_account.id),
        ], order='id')

    def _get_expense_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.expense_account.id),
        ], order='id')

    def _make_lc(self, move, amount):
        picking = move.picking_id
        lc = Form(self.env['stock.landed.cost'])
        lc.account_journal_id = self.stock_journal
        lc.picking_ids.add(move.picking_id)
        with lc.cost_lines.new() as cost_line:
            cost_line.product_id = self.productlc1
            cost_line.price_unit = amount
        lc = lc.save()
        lc.compute_landed_cost()
        lc.button_validate()
        return lc


class TestStockValuationLCFIFO(TestStockValuationLC):
    def setUp(self):
        super(TestStockValuationLCFIFO, self).setUp()
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_normal_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        lc = self._make_lc(move1, 100)
        move3 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)
        self.assertEqual(self.product1.standard_price, 20)

    def test_negative_1(self):
        self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15, create_picking=True)
        lc = self._make_lc(move2, 100)

        self.assertEqual(self.product1.value_svl, 200)
        self.assertEqual(self.product1.quantity_svl, 8)

    def test_alreadyout_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_alreadyout_2(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move2 = self._make_out_move(self.product1, 1)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_alreadyout_3(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        move1.move_line_ids.qty_done = 15
        lc = self._make_lc(move1, 60)

        self.assertEqual(self.product1.value_svl, 70)
        self.assertEqual(self.product1.quantity_svl, 5)

    def test_fifo_to_standard_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15)
        move3 = self._make_out_move(self.product1, 5)
        lc = self._make_lc(move1, 100)
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'

        out_svl = self.product1.stock_valuation_layer_ids.sorted()[-2]
        in_svl = self.product1.stock_valuation_layer_ids.sorted()[-1]

        self.assertEqual(out_svl.value, -250)
        self.assertEqual(in_svl.value, 225)

    def test_rounding_1(self):
        """3@100, out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=20, create_picking=True)
        lc = self._make_lc(move1, 40)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), [60.0, 40.0, -33.33, -33.34, -33.33])
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_rounding_2(self):
        """3@98, out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=20, create_picking=True)
        lc = self._make_lc(move1, 38)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(move2.stock_valuation_layer_ids.value, -32.67)
        self.assertEqual(move3.stock_valuation_layer_ids.value, -32.67)
        self.assertAlmostEqual(move4.stock_valuation_layer_ids.value, -32.66, delta=0.01)  # self.env.company.currency_id.round(-32.66) -> -32.660000000000004
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_rounding_3(self):
        """3@4.85, out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=1, create_picking=True)
        lc = self._make_lc(move1, 1.85)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), [3.0, 1.85, -1.62, -1.62, -1.61])
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_in_and_out_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=100, create_picking=True)
        self.assertEqual(move1.stock_valuation_layer_ids[0].remaining_value, 1000)
        lc1 = self._make_lc(move1, 100)
        self.assertEqual(move1.stock_valuation_layer_ids[0].remaining_value, 1100)
        lc2 = self._make_lc(move1, 50)
        self.assertEqual(move1.stock_valuation_layer_ids[0].remaining_value, 1150)
        self.assertEqual(self.product1.value_svl, 1150)
        self.assertEqual(self.product1.quantity_svl, 10)
        move2 = self._make_out_move(self.product1, 1)
        self.assertEqual(move2.stock_valuation_layer_ids.value, -115)


class TestStockValuationLCAVCO(TestStockValuationLC):
    def setUp(self):
        super(TestStockValuationLCAVCO, self).setUp()
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_normal_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        lc = self._make_lc(move1, 100)
        move3 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.value_svl, 380)

    def test_negative_1(self):
        self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15, create_picking=True)
        lc = self._make_lc(move2, 100)

        self.assertEqual(self.product1.value_svl, 200)
        self.assertEqual(self.product1.quantity_svl, 8)

    def test_alreadyout_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        lc = self._make_lc(move1, 100)

        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 2)
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_alreadyout_2(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move2 = self._make_out_move(self.product1, 1)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.value_svl, 375)
        self.assertEqual(self.product1.quantity_svl, 19)


class TestStockValuationLCFIFOVB(TestStockValuationLC):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationLCFIFOVB, cls).setUpClass()
        cls.vendor1 = cls.  env['res.partner'].create({'name': 'vendor1'})
        cls.vendor1.property_account_payable_id = cls.payable_account
        cls.vendor2 = cls.env['res.partner'].create({'name': 'vendor2'})
        cls.vendor2.property_account_payable_id = cls.payable_account
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        cls.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_vendor_bill_flow_anglo_saxon_1(self):
        """In anglo saxon accounting, receive 10@10 and invoice. Then invoice 1@50 as a landed costs
        and create a linked landed costs record.
        """
        self.env.company.anglo_saxon_accounting = True

        # Create an RFQ for self.product1, 10@10
        rfq = Form(self.env['purchase.order'])
        rfq.partner_id = self.vendor1

        with rfq.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.price_unit = 10
            po_line.product_qty = 10
            po_line.taxes_id.clear()

        rfq = rfq.save()
        rfq.button_confirm()

        # Process the receipt
        receipt = rfq.picking_ids
        wiz = receipt.button_validate()
        wiz = self.env['stock.immediate.transfer'].browse(wiz['res_id']).process()
        self.assertEqual(rfq.order_line.qty_received, 10)

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 0)
        self.assertEqual(input_aml.credit, 100)
        valuation_aml = self._get_stock_valuation_move_lines()[-1]
        self.assertEqual(valuation_aml.debit, 100)
        self.assertEqual(valuation_aml.credit, 0)

        # Create a vebdor bill for the RFQ
        action = rfq.action_view_invoice()
        vb = Form(self.env['account.move'].with_context(action['context']))
        vb = vb.save()
        vb.post()

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 100)
        self.assertEqual(input_aml.credit, 0)
        payable_aml = self._get_payable_move_lines()[-1]
        self.assertEqual(payable_aml.debit, 0)
        self.assertEqual(payable_aml.credit, 100)

        # Create a vendor bill for a landed cost product, post it and validate a landed cost
        # linked to this vendor bill. LC; 1@50
        lcvb = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        lcvb.partner_id = self.vendor2
        with lcvb.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 50
            inv_line.is_landed_costs_line = True
        with lcvb.invoice_line_ids.edit(0) as inv_line:
            inv_line.tax_ids.clear()
        lcvb = lcvb.save()
        lcvb.post()

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 50)
        self.assertEqual(input_aml.credit, 0)
        payable_aml = self._get_payable_move_lines()[-1]
        self.assertEqual(payable_aml.debit, 0)
        self.assertEqual(payable_aml.credit, 50)

        action = lcvb.button_create_landed_costs()
        lc = Form(self.env[action['res_model']].browse(action['res_id']))
        lc.picking_ids.add(receipt)
        lc = lc.save()
        lc.button_validate()

        self.assertEqual(lc.cost_lines.price_unit, 50)
        self.assertEqual(lc.cost_lines.product_id, self.productlc1)

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 0)
        self.assertEqual(input_aml.credit, 50)
        valuation_aml = self._get_stock_valuation_move_lines()[-1]
        self.assertEqual(valuation_aml.debit, 50)
        self.assertEqual(valuation_aml.credit, 0)

        # Check reconciliation of input aml of lc
        lc_input_aml = lc.account_move_id.line_ids.filtered(lambda aml: aml.account_id == self.stock_input_account)
        self.assertTrue(len(lc_input_aml.full_reconcile_id), 1)

        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 150)

    def test_vendor_bill_flow_anglo_saxon_2(self):
        """In anglo saxon accounting, receive 10@10 and invoice with the addition of 1@50 as a
        landed costs and create a linked landed costs record.
        """
        self.env.company.anglo_saxon_accounting = True

        # Create an RFQ for self.product1, 10@10
        rfq = Form(self.env['purchase.order'])
        rfq.partner_id = self.vendor1

        with rfq.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.price_unit = 10
            po_line.product_qty = 10
            po_line.taxes_id.clear()

        rfq = rfq.save()
        rfq.button_confirm()

        # Process the receipt
        receipt = rfq.picking_ids
        wiz = receipt.button_validate()
        wiz = self.env['stock.immediate.transfer'].browse(wiz['res_id']).process()
        self.assertEqual(rfq.order_line.qty_received, 10)

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 0)
        self.assertEqual(input_aml.credit, 100)
        valuation_aml = self._get_stock_valuation_move_lines()[-1]
        self.assertEqual(valuation_aml.debit, 100)
        self.assertEqual(valuation_aml.credit, 0)

        # Create a vebdor bill for the RFQ and add to it the landed cost
        action = rfq.action_view_invoice()
        vb = Form(self.env['account.move'].with_context(action['context']))
        with vb.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 50
            inv_line.is_landed_costs_line = True
        vb = vb.save()
        vb.post()

        action = vb.button_create_landed_costs()
        lc = Form(self.env[action['res_model']].browse(action['res_id']))
        lc.picking_ids.add(receipt)
        lc = lc.save()
        lc.button_validate()

        # Check reconciliation of input aml of lc
        lc_input_aml = lc.account_move_id.line_ids.filtered(lambda aml: aml.account_id == self.stock_input_account)
        self.assertTrue(len(lc_input_aml.full_reconcile_id), 1)

    def test_vendor_bill_flow_continental_1(self):
        """In continental accounting, receive 10@10 and invoice. Then invoice 1@50 as a landed costs
        and create a linked landed costs record.
        """
        self.env.company.anglo_saxon_accounting = False

        # Create an RFQ for self.product1, 10@10
        rfq = Form(self.env['purchase.order'])
        rfq.partner_id = self.vendor1

        with rfq.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.price_unit = 10
            po_line.product_qty = 10
            po_line.taxes_id.clear()

        rfq = rfq.save()
        rfq.button_confirm()

        # Process the receipt
        receipt = rfq.picking_ids
        wiz = receipt.button_validate()
        wiz = self.env['stock.immediate.transfer'].browse(wiz['res_id']).process()
        self.assertEqual(rfq.order_line.qty_received, 10)

        input_aml = self._get_stock_input_move_lines()[-1]
        self.assertEqual(input_aml.debit, 0)
        self.assertEqual(input_aml.credit, 100)
        valuation_aml = self._get_stock_valuation_move_lines()[-1]
        self.assertEqual(valuation_aml.debit, 100)
        self.assertEqual(valuation_aml.credit, 0)

        # Create a vebdor bill for the RFQ
        action = rfq.action_view_invoice()
        vb = Form(self.env['account.move'].with_context(action['context']))
        vb = vb.save()
        vb.post()

        expense_aml = self._get_expense_move_lines()[-1]
        self.assertEqual(expense_aml.debit, 100)
        self.assertEqual(expense_aml.credit, 0)

        payable_aml = self._get_payable_move_lines()[-1]
        self.assertEqual(payable_aml.debit, 0)
        self.assertEqual(payable_aml.credit, 100)

        # Create a vendor bill for a landed cost product, post it and validate a landed cost
        # linked to this vendor bill. LC; 1@50
        lcvb = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        lcvb.partner_id = self.vendor2
        with lcvb.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 50
            inv_line.is_landed_costs_line = True
        with lcvb.invoice_line_ids.edit(0) as inv_line:
            inv_line.tax_ids.clear()
        lcvb = lcvb.save()
        lcvb.post()

        expense_aml = self._get_expense_move_lines()[-1]
        self.assertEqual(expense_aml.debit, 50)
        self.assertEqual(expense_aml.credit, 0)
        payable_aml = self._get_payable_move_lines()[-1]
        self.assertEqual(payable_aml.debit, 0)
        self.assertEqual(payable_aml.credit, 50)

        action = lcvb.button_create_landed_costs()
        lc = Form(self.env[action['res_model']].browse(action['res_id']))
        lc.picking_ids.add(receipt)
        lc = lc.save()
        lc.button_validate()

        self.assertEqual(lc.cost_lines.price_unit, 50)
        self.assertEqual(lc.cost_lines.product_id, self.productlc1)

        expense_aml = self._get_expense_move_lines()[-1]
        self.assertEqual(expense_aml.debit, 0)
        self.assertEqual(expense_aml.credit, 50)
        valuation_aml = self._get_stock_valuation_move_lines()[-1]
        self.assertEqual(valuation_aml.debit, 50)
        self.assertEqual(valuation_aml.credit, 0)

        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 150)

