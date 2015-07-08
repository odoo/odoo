# -*- coding: utf-8 -*-
import datetime
import time
import os

import openerp.report

from openerp.tools import float_compare
from openerp import tools
from openerp.tools import test_reports

from openerp.addons.point_of_sale.tests.common import TestPointOfSaleCommon


class TestPointOfSaleFlow(TestPointOfSaleCommon):

    def test_register_open(self):
        """
            In order to test the Point of Sale module, I will open all cash registers through the wizard
            """
        # open all statements/cash registers
        self.statement.open_statement()

    def test_order_to_payment(self):
        """
            In order to test the Point of Sale in module, I will do a full flow from the sale to the payment and invoicing.
            I will use two products, one with price including a 10% tax, the other one with 5% tax excluded from the price.
        """
        # I open a new PoS Session wizard
        pos_order_session_wizard0 = self.PosSessionOpennig.create({
            'pos_config_id': self.pos_config_id.id
        })

        # I click on create a new session button
        pos_order_session_wizard0.open_existing_session_cb()

        # I open the session after having counted the money
        self.pos_order_session0.wkf_action_open()

        # I create a PoS order with 2 units of PCSC234 at 450 EUR (Tax Incl)
        # and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos0 = self.PosOrder.create({
            'company_id': self.company_id.id,
            'pricelist_id': self.partner_id.property_product_pricelist.id,
            'partner_id': self.partner_id.id
        })

        vals = {'product_id': self.product3_id.id,
                'order_id': self.pos_order_pos0.id}
        line1 = self.env['pos.order.line'].new(vals)
        line1.onchange_product_id()
        line1_data = line1._convert_to_write(line1._cache)

        self.pos_order_pos0_line1 = self.env['pos.order.line'].create({
            'name': "OL/0001",
            'product_id': self.product3_id.id,
            'price_unit': 450,
            'discount': 0.0,
            'qty': 2.0,
            'tax_ids': line1_data.get('tax_ids'),
            'order_id': self.pos_order_pos0.id
        })

        vals1 = {'product_id': self.product4_id.id,
                 'order_id': self.pos_order_pos0.id}
        line2 = self.env['pos.order.line'].new(vals1)
        line2.onchange_product_id()
        line2_data = line1._convert_to_write(line2._cache)

        self.pos_order_pos0_line2 = self.env['pos.order.line'].create({
            'name': "OL/0002",
            'product_id': self.product4_id.id,
            'price_unit': 300,
            'discount': 0.0,
            'qty': 3.0,
            'tax_ids': line2_data.get('tax_ids'),
            'order_id': self.pos_order_pos0.id
        })

        # I check that the total of the order is equal to 450*2 + 300*3*1.05
        # and the tax of the order is equal to 900 -(450 * 2 / 1.1) +
        # 300*0.05*3
        self.assertLess(
            abs(self.pos_order_pos0.amount_total - (450 * 2 + 300 * 3 * 1.05)),
            0.01, 'The order has a wrong amount, tax included.')

        self.assertLess(
            abs(self.pos_order_pos0.amount_tax -
                (900 - (450 * 2 / 1.1) + 300 * 0.05 * 3)),
            0.01, 'The order has a wrong tax amount.')

        # I want to add a global discount of 5 percent using the wizard

        self.pos_discount_0 = self.PosDiscount.create({
            'discount': 5.0
        })

        context = {"active_model": "pos.order",
                   "active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}

        # I click the apply button to set the discount on all lines
        self.pos_discount_0.with_context(context).apply_discount()

        # I check that the total of the order is now equal to (450*2 +
        # 300*3*1.05)*0.95
        self.assertLess(
            abs(self.pos_order_pos0.amount_total -
                (450 * 2 + 300 * 3 * 1.05) * 0.95),
            0.01, 'The order has a wrong total including tax and discounts')

        # I click on the "Make Payment" wizard to pay the PoS order with a
        # partial amount of 100.0 EUR
        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': 100.0
        })

        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).check()

        # I check that the order is not marked as paid yet
        self.assertEqual(self.pos_order_pos0.state, 'draft')

        # On the second payment proposition, I check that it proposes me the
        # remaining balance which is 1790.0 EUR
        defs = self.pos_make_payment_0.with_context(
            {'active_id': self.pos_order_pos0.id}).default_get(['amount'])

        self.assertLess(
            abs(defs['amount'] - ((450 * 2 + 300 * 3 * 1.05) * 0.95 - 100.0)), 0.01, "The remaining balance is incorrect.")

        #'I pay the remaining balance.
        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}

        self.pos_make_payment_1 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': (450 * 2 + 300 * 3 * 1.05) * 0.95 - 100.0
        })

        # I click on the validate button to register the payment.
        self.pos_make_payment_1.with_context(context_make_payment).check()

        # I check that the order is marked as paid
        self.assertEqual(self.pos_order_pos0.state, 'paid')

        # I generate the journal entries
        self.pos_order_pos0.create_account_move()

        # I test that the generated journal entry is attached to the PoS order
        self.assertTrue(self.pos_order_pos0.account_move, True)

    def test_order_to_invoice(self):

        #I create a new PoS order with 2 units of PC1 at 450 EUR (Tax Incl) and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'pricelist_id': self.partner_id.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3_id.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 2.0,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4_id.id,
                'price_unit': 300,
                'discount': 5.0,
                'qty': 3.0,
            })]
        })

        # I click on the "Make Payment" wizard to pay the PoS order
        context_make_payment = {
            "active_ids": [self.pos_order_pos1.id], "active_id": self.pos_order_pos1.id}
        self.pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': (450 * 2 + 300 * 3 * 1.05) * 0.95,
        })
        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos1.id}
        self.pos_make_payment.with_context(context_payment).check()

        # I check that the order is marked as paid and there is no invoice
        # attached to it
        self.assertEqual(
            self.pos_order_pos1.state, 'paid', "State not correct")
        self.assertFalse(self.pos_order_pos1.invoice_id)

        # I set the order as invoiced
        self.pos_order_pos1.signal_workflow('invoice')

        # I generate an invoice from the order
        self.invoice = self.pos_order_pos1.action_invoice()

        # I test that the total of the attached invoice is correct
        self.amount_total = self.pos_order_pos1.amount_total
        self.assertEqual(
            float_compare(self.amount_total, 1752.75, precision_digits=2), 0, "Invoice not correct")

        """In order to test the reports on Bank Statement defined in point_of_sale module, I create a bank statement line, confirm it and print the reports"""

        # I select the period and journal for the bank statement

        context_journal = {'journal_type': 'bank'}
        self.assertTrue(self.AccountBankStatement.with_context(
            context_journal)._default_journal(), 'Journal has not been selected')
        journal = self.env['account.journal'].create({
            'name': 'Bank Test',
            'code': 'BNKT',
            'type': 'bank',
            'company_id': self.env.ref('base.main_company').id
        })
        # I create a bank statement with Opening and Closing balance 0.
        account_statement = self.AccountBankStatement.create({
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'date': time.strftime('%Y-%m-%d'),
            'journal_id': journal.id,
            'company_id': self.env.ref('base.main_company').id,
        })
        # I create bank statement line
        account_statement_line = self.AccountBankStatementLine.create({
            'amount': 1000,
            'partner_id': self.partner_4.id,
            'statement_id': account_statement.id,
            'name': 'EXT001'
        })
        # I modify the bank statement and set the Closing Balance.
        account_statement.write({
            'balance_end_real': 1000.0,
        })

        # I reconcile the bank statement.
        new_aml_dicts = [{
            'account_id': self.partner_4.property_account_receivable_id.id,
            'name': "EXT001",
            'credit': 1000.0,
            'debit': 0.0,
        }]

        self.AccountBankStatementLine._model.process_reconciliations(
            self.env.cr, self.env.uid, [account_statement_line.id], [{'new_aml_dicts': new_aml_dicts}])

        # I confirm the bank statement using Confirm button

        self.AccountBankStatement.button_confirm_bank()

        # Print the account statement report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, account_statement.id, 'point_of_sale.report_statement', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-statement.' +
                 format), 'wb+').write(self.data)

        # Printing the user s product report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, account_statement.id, 'point_of_sale.report_usersproduct', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-usersproduct.' +
                 format), 'wb+').write(self.data)

        # point of sale reports!

        # In order to test the PDF reports defined on a Point Of Sale, we will
        # print a POS Invoice Report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, self.pos_order_pos1.id, 'point_of_sale.report_invoice', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-invoice_report.' +
                 format), 'wb+').write(self.data)
        # In order to test the PDF reports defined on a Point Of Sale, we will
        # print a POS Lines Report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, self.pos_order_pos1.id, 'point_of_sale.report_saleslines', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-lines_report.' +
                 format), 'wb+').write(selfdata)

        # In order to test the PDF reports defined on a Point of Sale, we will
        # print a POS Receipt Report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, self.pos_order_pos1.id, 'point_of_sale.report_receipt', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-receipt_report.' +
                 format), 'wb+').write(self.data)

        # Print the POS Details Report through the wizard
        ctx = {}
        ctx.update({'model': 'ir.ui.menu', 'active_ids': []})
        data_dict = {
            'date_start': datetime.date.today(), 'date_end': datetime.date.today(), 'user_ids': self.user_ids}
        test_reports.try_report_action(
            self.env.cr, self.env.uid, 'pos_details_action', wiz_data=data_dict, context=ctx, our_module='point_of_sale')

        # In order to test the PDF reports defined on a Point of Sale, we will
        # print a POS Payment Report

        self.data, format = openerp.report.render_report(
            self.env.cr, self.env.uid, self.pos_order_pos1.id, 'point_of_sale.report_payment', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'point_of_sale-payment_report.' +
                 format), 'wb+').write(self.data)