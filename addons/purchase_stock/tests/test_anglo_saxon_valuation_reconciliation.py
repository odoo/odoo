# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import Form, tagged
from odoo import fields

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.stock_account_product_categ.property_account_creditor_price_difference_categ = cls.company_data['default_account_stock_price_diff']

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        company_data = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)

        # Create stock config.
        company_data.update({
            'default_account_stock_price_diff': cls.env['account.account'].create({
                'name': 'default_account_stock_price_diff',
                'code': 'STOCKDIFF',
                'reconcile': True,
                'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
                'company_id': company_data['company'].id,
            }),
        })
        return company_data

    def _create_purchase(self, product, date, quantity=1.0, set_tax=False, price_unit=66.0):
        rslt = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': quantity,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': price_unit,
                    'date_planned': date,
                    'taxes_id': [(6, 0, product.supplier_taxes_id.ids)] if set_tax else False,
                })],
             'date_order': date,
        })
        rslt.button_confirm()
        return rslt

    def _create_invoice_for_po(self, purchase_order, date):
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice', default_date=date))
        move_form.invoice_date = date
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.currency_data['currency']
        move_form.purchase_id = purchase_order
        return move_form.save()

    def test_shipment_invoice(self):
        """ Tests the case into which we receive the goods first, and then make the invoice.
        """
        test_product = self.test_product_delivery
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-02-02')
        invoice.action_post()
        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)
        # cancel the invoice
        invoice.button_cancel()

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then receive the goods.
        """
        # Create a PO and an invoice for it
        test_product = self.test_product_order
        purchase_order = self._create_purchase(test_product, '2017-12-01')

        invoice = self._create_invoice_for_po(purchase_order, '2017-12-23')
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
        invoice = move_form.save()

        # Validate the invoice and refund the goods
        invoice.action_post()
        self._process_pickings(purchase_order.picking_ids, date='2017-12-24')
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.check_reconciliation(invoice, picking)

        # Return the goods and refund the invoice
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 1
        return_pick._action_done()
        self._change_pickings_date(return_pick, '2018-01-13')

        # Refund the invoice
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'refund_method': 'cancel',
            'date': '2018-03-15',
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])

        # Check the result
        self.assertEqual(invoice.payment_state, 'reversed', "Invoice should be in 'reversed' state")
        self.assertEqual(refund_invoice.payment_state, 'paid', "Refund should be in 'paid' state")
        self.check_reconciliation(refund_invoice, return_pick)

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we receive part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.test_product_delivery
        date_po_and_delivery0 = '2017-01-01'
        purchase_order = self._create_purchase(test_product, date_po_and_delivery0, quantity=5.0)
        self._process_pickings(purchase_order.picking_ids, quantity=2.0, date=date_po_and_delivery0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order="id asc", limit=1)

        invoice = self._create_invoice_for_po(purchase_order, '2017-01-15')
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        invoice = move_form.save()
        invoice.action_post()
        self.check_reconciliation(invoice, picking, full_reconcile=False)

        invoice2 = self._create_invoice_for_po(purchase_order, '2017-02-15')
        move_form = Form(invoice2)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        invoice2 = move_form.save()
        invoice2.action_post()
        self.check_reconciliation(invoice2, picking, full_reconcile=False)

        # We don't need to make the date of processing explicit since the very last rate
        # will be taken
        self._process_pickings(purchase_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order='id desc', limit=1)
        self.check_reconciliation(invoice2, picking)

    def test_rounding_discount(self):
        self.env.ref("product.decimal_discount").digits = 5
        tax_exclude_id = self.env["account.tax"].create(
            {
                "name": "Exclude tax",
                "amount": "0.00",
                "type_tax_use": "purchase",
            }
        )

        test_product = self.test_product_delivery
        test_product.supplier_taxes_id = [(6, 0, tax_exclude_id.ids)]
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery, quantity=10000, set_tax=True)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-01-01')

        # Set a discount
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.discount = 0.92431
        move_form.save()

        invoice.action_post()

        # Check the price difference amount.
        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_account_product_categ.property_account_creditor_price_difference_categ)
        self.assertTrue(len(price_diff_line) == 1, "A price difference line should be created")
        self.assertAlmostEqual(price_diff_line.price_total, -6100.446)

        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    def test_rounding_price_unit(self):
        self.env.ref("product.decimal_price").digits = 6

        test_product = self.test_product_delivery
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery, quantity=1000000, price_unit=0.0005)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-01-01')

        # Set a discount
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 0.0006
        move_form.save()

        invoice.action_post()

        # Check the price difference amount. It's expected that price_unit * qty != price_total.
        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_account_product_categ.property_account_creditor_price_difference_categ)
        self.assertTrue(len(price_diff_line) == 1, "A price difference line should be created")
        self.assertAlmostEqual(price_diff_line.price_unit, 0.0001)
        self.assertAlmostEqual(price_diff_line.price_total, 100.0)

        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    @freeze_time('2021-01-01')
    def test_rounding_price_unit_exchange_difference(self):
        test_product = self.test_product_delivery
        date_po_and_delivery = '2021-01-01'
        rate_po = 28.0
        date_bill = '2020-01-01'
        rate_bill = 26.0
        foreign_currency = self.currency_data['currency']
        company_currency = self.env.company.currency_id
        self.env['res.currency.rate'].create([
        {
            'name': date_po_and_delivery,
            'rate': rate_po,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_bill,
            'rate': rate_bill,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_po_and_delivery,
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_bill,
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        }])

        purchase_order = self._create_purchase(test_product, date_po_and_delivery, quantity=100, price_unit=6000)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)
        invoice = self._create_invoice_for_po(purchase_order, date_bill)
        invoice.action_post()

        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_account_product_categ.property_account_creditor_price_difference_categ)
        self.assertFalse(price_diff_line, "No price difference line should be created")

        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    @freeze_time('2021-01-03')
    def test_price_difference_exchange_difference_accounting_date(self):
        test_product = self.test_product_delivery
        test_product.categ_id.write({"property_cost_method": "standard"})
        test_product.write({'standard_price': 100.0})
        date_po_receipt = '2021-01-02'
        rate_po_receipt = 25.0
        date_bill = '2021-01-01'
        rate_bill = 30.0
        date_accounting = '2021-01-03'
        rate_accounting = 26.0

        foreign_currency = self.currency_data['currency']
        company_currency = self.env.company.currency_id
        self.env['res.currency.rate'].create([
        {
            'name': date_po_receipt,
            'rate': rate_po_receipt,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_bill,
            'rate': rate_bill,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_accounting,
            'rate': rate_accounting,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_po_receipt,
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_accounting,
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        }, {
            'name': date_bill,
            'rate': 1.0,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        }])

        #purchase order created in foreign currency
        purchase_order = self._create_purchase(test_product, date_po_receipt, quantity=10, price_unit=3000)
        with freeze_time(date_po_receipt):
            self._process_pickings(purchase_order.picking_ids)
        invoice = self._create_invoice_for_po(purchase_order, date_bill)
        with Form(invoice) as move_form:
            move_form.invoice_date = fields.Date.from_string(date_bill)
            move_form.date = fields.Date.from_string(date_accounting)
        invoice.action_post()

        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_account_product_categ.property_account_creditor_price_difference_categ)
        self.assertTrue(len(price_diff_line) == 1, "A price difference line should be created")
        self.assertAlmostEqual(price_diff_line.balance, 192.31)
        self.assertAlmostEqual(price_diff_line.price_total, 5000.0)

        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.check_reconciliation(invoice, picking)
        interim_account_id = self.company_data['default_account_stock_in'].id

        valuation_line = picking.move_lines.mapped('account_move_ids.line_ids').filtered(lambda x: x.account_id.id == interim_account_id)
        self.assertTrue(valuation_line.full_reconcile_id, "The reconciliation should be total at that point.")

        exchange_move = valuation_line.full_reconcile_id.exchange_move_id
        self.assertTrue(exchange_move, "An exchange move should exists.")
        exchange_difference = exchange_move.line_ids.filtered(lambda l: l.account_id.id == interim_account_id).balance
        self.assertAlmostEqual(exchange_difference, 38.46, "Exchange amount is incorrect")

    def test_reconcile_cash_basis_bill(self):
        ''' Test the generation of the CABA move after bill payment
        '''
        self.env.company.tax_exigibility = True
        cash_basis_base_account = self.env['account.account'].create({
            'code': 'cash_basis_base_account',
            'name': 'cash_basis_base_account',
            'user_type_id': self.env.ref('account.data_account_type_revenue').id,
            'company_id': self.company_data['company'].id,
        })
        self.company_data['company'].account_cash_basis_base_account_id = cash_basis_base_account

        cash_basis_transfer_account = self.env['account.account'].create({
            'code': 'cash_basis_transfer_account',
            'name': 'cash_basis_transfer_account',
            'user_type_id': self.env.ref('account.data_account_type_revenue').id,
            'company_id': self.company_data['company'].id,
        })

        tax_account_1 = self.env['account.account'].create({
            'code': 'tax_account_1',
            'name': 'tax_account_1',
            'user_type_id': self.env.ref('account.data_account_type_revenue').id,
            'company_id': self.company_data['company'].id,
        })

        fake_country = self.env['res.country'].create({
            'name': "The Island of the Fly",
            'code': 'YY',
        })

        tax_tags = self.env['account.account.tag'].create({
            'name': 'tax_tag_%s' % str(i),
            'applicability': 'taxes',
            'country_id': fake_country.id,
        } for i in range(8))

        cash_basis_tax_a_third_amount = self.env['account.tax'].create({
            'name': 'tax_1',
            'amount': 33.3333,
            'company_id': self.company_data['company'].id,
            'cash_basis_transition_account_id': cash_basis_transfer_account.id,
            'tax_exigibility': 'on_payment',
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags[0].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': tax_account_1.id,
                    'tag_ids': [(6, 0, tax_tags[1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags[2].ids)],
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': tax_account_1.id,
                    'tag_ids': [(6, 0, tax_tags[3].ids)],
                }),
            ],
        })

        product_A = self.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "default_code": "prda",
                "categ_id": self.stock_account_product_categ.id,
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(6, 0, cash_basis_tax_a_third_amount.ids)],
                "lst_price": 100.0,
                "standard_price": 10.0,
                "property_account_income_id": self.company_data["default_account_revenue"].id,
                "property_account_expense_id": self.company_data["default_account_expense"].id,
            }
        )
        product_A.categ_id.write(
            {
                "property_account_creditor_price_difference_categ": False,
                "property_valuation": "real_time",
                "property_cost_method": "standard",
            }
        )

        date_po_and_delivery = '2018-01-01'
        purchase_order = self._create_purchase(product_A, date_po_and_delivery, set_tax=True, price_unit=300.0)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        bill = self._create_invoice_for_po(purchase_order, '2018-02-02')
        bill.action_post()

        # Register a payment creating the CABA journal entry on the fly and reconcile it with the tax line.
        self.env['account.payment.register']\
            .with_context(active_ids=bill.ids, active_model='account.move')\
            .create({})\
            ._create_payments()

        partial_rec = bill.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        # Tax values based on payment
        # Invoice amount 300
        self.assertRecordValues(caba_move.line_ids, [
            # pylint: disable=C0326
            # Base amount:
            {'debit': 0.0,    'credit': 150.0,      'amount_currency': -300.0,   'account_id': cash_basis_base_account.id},
            {'debit': 150.0,      'credit': 0.0,    'amount_currency': 300.0,  'account_id': cash_basis_base_account.id},
            # tax:
            {'debit': 0.0,     'credit': 50.0,      'amount_currency': -100.0,   'account_id': cash_basis_transfer_account.id},
            {'debit': 50.0,      'credit': 0.0,     'amount_currency': 100.0,  'account_id': tax_account_1.id},
        ])
