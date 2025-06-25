# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import Form, tagged
from odoo import Command, fields



@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR', rounding=0.001)

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

        # Create stock config.
        company_data.update({
            'default_account_stock_price_diff': cls.env['account.account'].create({
                'name': 'default_account_stock_price_diff',
                'code': 'STOCKDIFF',
                'reconcile': True,
                'account_type': 'asset_current',
            }),
        })
        return company_data

    def _create_purchase(self, product, date, quantity=1.0, set_tax=False, price_unit=66.0, currency=False):
        if not currency:
            currency = self.other_currency
        with freeze_time(date):
            rslt = self.env['purchase.order'].create({
                'partner_id': self.partner_a.id,
                'currency_id': currency.id,
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
        with freeze_time(date):
            move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice', default_date=date))
            move_form.invoice_date = date
            move_form.partner_id = self.partner_a
            move_form.currency_id = self.other_currency
            move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-purchase_order.id)
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
        with freeze_time('2018-01-13'):
            stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
                active_ids=picking.ids, active_id=picking.ids[0], active_model='stock.picking'))
            stock_return_picking = stock_return_picking_form.save()
            stock_return_picking.product_return_moves.quantity = 1.0
            stock_return_picking_action = stock_return_picking.action_create_returns()
            return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
            return_pick.action_assign()
            return_pick.move_ids.quantity = 1
            return_pick.move_ids.picked = True
            return_pick._action_done()

        # Refund the invoice
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'date': '2018-03-15',
            'journal_id': invoice.journal_id.id,
        })
        new_invoice = self.env['account.move'].browse(refund_invoice_wiz.modify_moves()['res_id'])
        refund_invoice = invoice.reversal_move_ids
        # Check the result
        self.assertEqual(invoice.payment_state, 'reversed', "Invoice should be in 'reversed' state")
        self.assertEqual(refund_invoice.payment_state, 'paid', "Refund should be in 'paid' state")
        self.assertEqual(new_invoice.state, 'draft', "New invoice should be in 'draft' state")
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
        invoice_layer = self.env['stock.valuation.layer'].search([('account_move_line_id', 'in', invoice.line_ids.ids)])
        self.assertTrue(len(invoice_layer) == 1, "A price difference line should be created")
        self.assertAlmostEqual(invoice_layer.value, -3050.22)

        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.assertAlmostEqual(invoice_layer.value + picking.move_ids.stock_valuation_layer_ids.value, invoice.line_ids[0].debit)
        self.assertAlmostEqual(invoice_layer.value + picking.move_ids.stock_valuation_layer_ids.value, invoice.invoice_line_ids.price_subtotal/2, 2)
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
        invoice_layer = self.env['stock.valuation.layer'].search([('account_move_line_id', 'in', invoice.line_ids.ids)])
        self.assertTrue(len(invoice_layer) == 1, "A price difference line should be created")
        # self.assertAlmostEqual(invoice_layer.price_unit, 0.0001)
        self.assertAlmostEqual(invoice_layer.value, 50.0)

        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    @freeze_time('2021-01-03')
    def test_price_difference_exchange_difference_accounting_date(self):
        self.stock_account_product_categ.property_account_creditor_price_difference_categ = self.company_data['default_account_stock_price_diff']
        test_product = self.test_product_delivery
        test_product.categ_id.write({"property_cost_method": "standard"})
        test_product.write({'standard_price': 100.0})
        date_po_receipt = '2021-01-02'
        rate_po_receipt = 25.0
        date_bill = '2021-01-01'
        rate_bill = 30.0
        date_accounting = '2021-01-03'
        rate_accounting = 26.0

        foreign_currency = self.other_currency
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
        self.assertAlmostEqual(price_diff_line.price_subtotal, 5000.0)

        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        interim_account_id = self.company_data['default_account_stock_in'].id

        valuation_line = picking.move_ids.mapped('account_move_ids.line_ids').filtered(lambda x: x.account_id.id == interim_account_id)
        self.assertTrue(valuation_line.full_reconcile_id, "The reconciliation should be total at that point.")

    def test_reconcile_cash_basis_bill(self):
        ''' Test the generation of the CABA move after bill payment
        '''
        self.env.company.tax_exigibility = True
        cash_basis_base_account = self.env['account.account'].create({
            'code': 'cash.basis.base.account',
            'name': 'cash_basis_base_account',
            'account_type': 'income',
        })
        self.company_data['company'].account_cash_basis_base_account_id = cash_basis_base_account

        cash_basis_transfer_account = self.env['account.account'].create({
            'code': 'cash.basis.transfer.account',
            'name': 'cash_basis_transfer_account',
            'account_type': 'income',
        })

        tax_account_1 = self.env['account.account'].create({
            'code': 'tax.account.1',
            'name': 'tax_account_1',
            'account_type': 'income',
        })

        tax_tags = self.env['account.account.tag'].create({
            'name': 'tax_tag_%s' % str(i),
            'applicability': 'taxes',
        } for i in range(8))

        cash_basis_tax_a_third_amount = self.env['account.tax'].create({
            'name': 'tax_1',
            'amount': 33.3333,
            'company_id': self.company_data['company'].id,
            'cash_basis_transition_account_id': cash_basis_transfer_account.id,
            'type_tax_use': 'purchase',
            'tax_exigibility': 'on_payment',
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags[0].ids)],
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_account_1.id,
                    'tag_ids': [(6, 0, tax_tags[1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags[2].ids)],
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_account_1.id,
                    'tag_ids': [(6, 0, tax_tags[3].ids)],
                }),
            ],
        })

        product_A = self.env["product.product"].create(
            {
                "name": "Product A",
                "is_storable": True,
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

    def test_reconciliation_differed_billing(self):
        """
        Test whether products received billed at different time will be correctly reconciled
        valuation: automated
        - create a rfq
        - receive products
        - create bill - set quantity of product A = 0 - save
        - create bill - confirm
        -> the reconciliation should not take into account the lines of the first bill
        """
        date_po_and_delivery = '2022-03-02'
        self.product_a.write({
            'categ_id': self.stock_account_product_categ,
            'is_storable': True,
        })
        self.product_b.write({
            'categ_id': self.stock_account_product_categ,
            'is_storable': True,
        })
        purchase_order = self.env['purchase.order'].create({
            'currency_id': self.other_currency.id,
                'order_line': [
                    Command.create({
                        'name': self.product_a.name,
                        'product_id': self.product_a.id,
                        'product_qty': 1,
                    }),
                    Command.create({
                        'name': self.product_b.name,
                        'product_id': self.product_b.id,
                        'product_qty': 1,
                    }),
                ],
                'partner_id': self.partner_a.id,
            })
        purchase_order.button_confirm()
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        bill_1 = self._create_invoice_for_po(purchase_order, date_po_and_delivery)
        move_form = Form(bill_1)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 0
        move_form.save()

        bill_2 = self._create_invoice_for_po(purchase_order, date=date_po_and_delivery)
        bill_2.action_post()
        aml = bill_2.line_ids.filtered(lambda line: line.display_type == "product")
        pol = purchase_order.order_line
        self.assertRecordValues(pol, [{'qty_invoiced': line.qty_received} for line in pol])
        self.assertRecordValues(aml, [{'reconciled': True} for line in aml])

    def test_create_fifo_vacuum_anglo_saxon_expense_entry(self):

        # create purchase
        self.product_a.write({
            'standard_price': 27.0,
            'categ_id': self.stock_account_product_categ,
            'is_storable': True,
        })

        self.stock_account_product_categ['property_cost_method'] = 'average'

        #create purchase
        date_po_and_delivery = '2018-01-01'
        purchase_order = self._create_purchase(self.product_a, date_po_and_delivery, 1, price_unit=27)

        # proccess picking
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        # create return
        picking = purchase_order.picking_ids[0]
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.write({'quantity': 1000.0})
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_line_ids.write({'quantity': 1000})
        return_pick.button_validate()

        # create vendor bill
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
        move_form._view['modifiers']['purchase_id']['invisible'] = False
        move_form.partner_id = purchase_order.partner_id
        move_form.invoice_date = date_po_and_delivery
        move_form.purchase_id = purchase_order
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 999.0
        invoice = move_form.save()
        invoice.action_post()

        # register payment
        self.env['account.payment.register']\
            .with_context(active_ids=invoice.ids, active_model='account.move')\
            .create({})\
            ._create_payments()

        # create another purchase
        purchase_order2 = self.env['purchase.order'].create({
                'partner_id': self.partner_a.id,
                'currency_id': self.env.company.currency_id.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product_a.name,
                        'product_id': self.product_a.id,
                        'product_qty': 1,
                        'product_uom': self.product_a.uom_po_id.id,
                        'price_unit': 29,
                        'date_planned': date_po_and_delivery,
                    })],
                'date_order': date_po_and_delivery,
            })
        # confirm PO
        purchase_order2.button_confirm()
        # process pickings
        self._process_pickings(purchase_order2.picking_ids, date_po_and_delivery)

        picking2 = purchase_order2.picking_ids[0]
        self.assertEqual(picking2.state, 'done')

    @freeze_time('2000-05-05')
    def test_currency_exchange_journal_items(self):
        """ Prices modified by discounts and currency exchanges should still yield accurate price
        units when calculated by valuation mechanisms.
        """
        self.env.company.currency_id = self.env.ref('base.IQD').id
        # FIXME: when rounding method is `round_per_line` ?
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        self.test_product_order.standard_price = 500
        self.stock_account_product_categ.property_cost_method = 'average'
        self.env['res.currency.rate'].create({
            'name': '2000-05-05',
            'company_rate': .00756,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.env.company.id,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.env.ref('base.USD').id,
            'order_line': [(0, 0, {
                'product_id': self.test_product_order.id,
                'product_uom_qty': 13,
                'discount': 1,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.picking_ids.move_ids.quantity = 13
        purchase_order.picking_ids.button_validate()
        pre_bill_remaining_value = purchase_order.picking_ids.move_ids.stock_valuation_layer_ids.remaining_value
        purchase_order.action_create_invoice()
        purchase_order.invoice_ids.invoice_date = '2000-05-05'
        purchase_order.invoice_ids.action_post()
        post_bill_remaining_value = purchase_order.picking_ids.move_ids.stock_valuation_layer_ids.remaining_value
        self.assertEqual(post_bill_remaining_value, pre_bill_remaining_value)
        amls = self.env['account.move.line'].search([('product_id', '=', self.test_product_order.id)])
        self.assertRecordValues(
            amls,
            [{'debit': 0.0, 'credit': 6435.0}, {'debit': 6435.0, 'credit': 0.0}, {'debit': 6435.0, 'credit': 0.0}]
        )

    def test_manual_cost_adjustment_journal_items_quantity(self):
        """ The quantity field of `account.move.line` should be permitted to be zero, e.g., in the
        case of modifying an automatically valuated product's cost.
        """
        self.stock_account_product_categ.property_cost_method = 'average'
        self.product_a.write({
            'categ_id': self.stock_account_product_categ.id,
            'is_storable': True,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'price_unit': 4,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.picking_ids.move_line_ids.quantity = 5
        purchase_order.picking_ids.button_validate()
        with Form(self.product_a) as product_form:
            product_form.standard_price = 3

        cost_change_journal_items = self.env['account.move.line'].search([
            ('product_id', '=', self.product_a.id),
            '|', ('debit', '=', 5), ('credit', '=', 5),
        ])
        self.assertEqual(cost_change_journal_items.mapped('quantity'), [0, 0])

    @freeze_time('2025-01-07')
    def test_exchange_rate_backdated_bill(self):
        """ Having a purchase order in some foreign currency:
        Changing the invoice date on the bill for that order after having received the product
        should not affect the journal entries created after the user clicks the `Post` button on
        the bill- specifically:
        (A) In the case where that date is in the future (relative to the actual User time) and
        (B) The date has an associated currency rate which differs from the one used at reception
        """
        self.env.ref('base.EUR').active = True
        product = self.test_product_order
        self.env['res.currency.rate'].create([{
            'name': name,
            'rate': rate,
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
        } for (name, rate) in [('2025-01-06', 0.8), ('2025-01-07', 0.7), ('2025-01-08', 0.8)]])
        for date in ('2025-01-07', '2025-01-06', '2025-01-08'):
            purchase_order = self._create_purchase(product, '2025-01-07', quantity=1, price_unit=10, currency=self.env.ref('base.EUR'))
            receipt = purchase_order.picking_ids
            receipt.move_ids.quantity = 1
            receipt.button_validate()
            purchase_order.action_create_invoice()
            bill = purchase_order.invoice_ids
            with Form(bill) as bill_form:
                bill_form.invoice_date = date
            bill.action_post()

        # Prior to the commit introducing this test, we would have entries in the following journals:
        #   | Inventory Valuation | Vendor Bills | Exchange Difference |
        # Post commit, we should see no entries in the Exchange Difference journal
        stock_journal_id, bills_journal_id, exchg_journal_id = (
            product.categ_id.property_stock_journal.id,
            self.company_data['default_journal_purchase'].id,
            self.env.company.currency_exchange_journal_id.id,
        )
        relevant_amls = self.env['account.move.line'].search([
            ('journal_id', 'in', (stock_journal_id, bills_journal_id, exchg_journal_id)),
        ], order='id asc')
        self.assertEqual(len(relevant_amls), 16)
        self.assertEqual(self.env['account.journal'].browse(exchg_journal_id).entries_count, 0)
        self.assertRecordValues(
            relevant_amls,
            [
                # Control (no reconciliation needed)
                {'journal_id': stock_journal_id,    'balance': -14.29},
                {'journal_id': stock_journal_id,    'balance':  14.29},
                {'journal_id': bills_journal_id,    'balance':  14.29},
                {'journal_id': bills_journal_id,    'balance': -14.29},
                # back-dated bill
                {'journal_id': stock_journal_id,    'balance': -14.29},
                {'journal_id': stock_journal_id,    'balance':  14.29},
                {'journal_id': bills_journal_id,    'balance':  12.50},
                {'journal_id': bills_journal_id,    'balance': -12.50},
                {'journal_id': stock_journal_id,    'balance':   1.79},
                {'journal_id': stock_journal_id,    'balance':  -1.79},
                # forward-dated bill
                {'journal_id': stock_journal_id,    'balance': -14.29},
                {'journal_id': stock_journal_id,    'balance':  14.29},
                {'journal_id': bills_journal_id,    'balance':  12.50},
                {'journal_id': bills_journal_id,    'balance': -12.50},
                {'journal_id': stock_journal_id,    'balance':   1.79},
                {'journal_id': stock_journal_id,    'balance':  -1.79},
            ],
        )

    def test_exchange_rate_difference_post_bill_prior_to_reception(self):
        """ Billing/invoicing before validating a reception for some product that is valuated which
        has incurred some (foreign) currency exchange difference in the time between those two
        actions should result in that difference appearing under the 'Stock Valuation' account

        (as opposed to the regular exchange account)
        """
        avco_prod = self.test_product_order
        avco_prod.purchase_method = 'purchase'
        tomorrow = fields.Date.today() + timedelta(days=1)
        self.env.ref('base.EUR').active = True
        self.env['res.currency.rate'].create([
            {'name': fields.Date.today(), 'currency_id': self.ref('base.EUR'), 'rate': 0.9},
            {'name': tomorrow, 'currency_id': self.ref('base.EUR'), 'rate': 0.8},
        ])
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.ref('base.EUR'),
            'order_line': [Command.create({
                'product_id': avco_prod.id,
                'product_qty': 10,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        with (freeze_time(tomorrow)):
            receipt = purchase_order.picking_ids
            receipt.button_validate()

            cd = self.company_data
            stock_input_account, tax_purchase_account, account_payable_account, stock_valuation_account = (
                cd['default_account_stock_in'],
                cd['default_account_tax_purchase'],
                cd['default_account_payable'],
                cd['default_account_stock_valuation'],
            )
            self.assertRecordValues(
                self.env['account.move.line'].search([], order='id asc'),
                [
                    {'account_id': stock_input_account.id,          'debit': 420.0,         'credit':   0.0},
                    {'account_id': tax_purchase_account.id,         'debit':  63.0,         'credit':   0.0},
                    {'account_id': account_payable_account.id,      'debit':   0.0,         'credit': 483.0},
                    {'account_id': stock_input_account.id,          'debit':   0.0,         'credit': 420.0},
                    {'account_id': stock_valuation_account.id,      'debit': 420.0,         'credit':   0.0},
                    {'account_id': stock_input_account.id,          'debit': 46.67,         'credit':   0.0},
                    {'account_id': stock_valuation_account.id,      'debit':   0.0,         'credit': 46.67},
                ]
            )
