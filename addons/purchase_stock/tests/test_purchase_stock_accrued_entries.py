from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseStock(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        uom_unit = cls.env.ref('uom.product_uom_unit')
        product = cls.env['product.product'].create({
            'name': "Product",
            'list_price': 30.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 10.0,
                    'product_uom_id': product.uom_id.id,
                    'price_unit': product.list_price,
                    'tax_ids': False,
                }),
            ]
        })
        cls.purchase_order.button_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']

    def test_purchase_stock_accruals(self):
        # receive 2 on 2020-01-02
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({
            'quantity': 2,
            'picked': True,
        })
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # receive 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
        }).create({
            'account_id': self.account_expense.id,
            'date': '2020-01-01',
        })
        # nothing to invoice on 2020-01-01
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 2 to invoice on 2020-01-04
        wizard.date = fields.Date.to_date('2020-01-04')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        # 5 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 150},
            {'account_id': wizard.account_id.id, 'debit': 150, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 150, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 150},
        ])

    def test_purchase_stock_invoiced_accrued_entries(self):
        # deliver 2 on 2020-01-02
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # invoice on 2020-01-04
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-04')
        move.action_post()

        # deliver 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        # invoice on 2020-01-08
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-08')
        move.action_post()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-02',
        })

        # 2 to invoice on 2020-01-07
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        # nothing to invoice on 2020-01-05
        wizard.date = fields.Date.to_date('2020-01-05')
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 3 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 90},
            {'account_id': wizard.account_id.id, 'debit': 90, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 90, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 90},
        ])

        # nothing to invoice on 2020-01-09
        wizard.date = fields.Date.to_date('2020-01-09')
        with self.assertRaises(UserError):
            wizard.create_entries()

    @freeze_time('2025-07-01')
    def test_purchase_stock_accruals_anglo_saxon_price_diff(self):
        """ With anglo-saxon accounting, ensure that accrued wizard generates entries for
        difference between product standard cost and invoiced price or delivered price."""
        def _create_invoice_for_po(purchase_order, date):
            with freeze_time(date):
                move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice', default_date=date))
                move_form.invoice_date = date
                move_form.partner_id = self.partner_a
                move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-purchase_order.id)
                return move_form.save()

        account_receivable = self.company_data['default_account_receivable']
        account_stock_variation = self.product_a.categ_id.account_stock_variation_id
        # Config a product to be in perpetual valuation and use a price diff. account.
        stock_price_diff_acc_id = self.env['account.account'].create({
            'name': 'default_account_stock_price_diff',
            'code': 'STOCKDIFF',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        # `product_a` standard price: $ 800.00, vendor price: $ 1,000.00
        self.product_a.categ_id.update({
            'property_valuation': 'real_time',
            'property_price_difference_account_id': stock_price_diff_acc_id.id,
        })

        # Create and confirm a PO of 10 products.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_qty': 10,  # 10 units * $ 1,000.00 = $ 10,000.00
                    'product_uom_id': self.product_a.uom_id.id,
                    'price_unit': self.product_a.list_price,
                    'tax_ids': False,
                }),
            ]
        })
        purchase_order.button_confirm()
        # Create two invoices in the past.
        invoice_1 = _create_invoice_for_po(purchase_order, '2025-04-01')
        invoice_1.line_ids[0].quantity = 2
        invoice_1.action_post()
        invoice_2 = _create_invoice_for_po(purchase_order, '2025-06-01')
        invoice_2.line_ids[0].quantity = 5
        invoice_2.line_ids[0].price_unit = 900.00  # Invoice at different price.
        invoice_2.action_post()

        # Receive 1 unit yesterday.
        with freeze_time('2025-06-30'):
            receipt_1 = purchase_order.picking_ids
            receipt_1.move_ids.update({'quantity': 1, 'picked': True})
            wizard_create_backorder = Form.from_action(self.env, receipt_1.button_validate()).save()
            wizard_create_backorder.process()
        # Receive two more units today.
        receipt_2 = purchase_order.picking_ids[-1]
        receipt_2.move_ids.update({'quantity': 2, 'picked': True})
        wizard_create_backorder = Form.from_action(self.env, receipt_2.button_validate()).save()
        wizard_create_backorder.process()

        # Use accrued order wizard and check generated values for date in the past.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
        }).create({
            'account_id': account_receivable.id,
            'date': '2025-05-31',
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        # Expense: $ 2,000.00 (invoiced 2x $ 1,000.00 but nothing received yet.)
        # Price diff.: $ 400.00 ($ 2,000.00 - (2x $ 800.00) = $ 2,000.00 - $ 1,600.00)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 2000},
            {'account_id': account_receivable.id, 'debit': 2000, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 400},
            {'account_id': account_stock_variation.id, 'debit': 400, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 2000, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 2000},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 400, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 400},
        ])

        # Use accrued order wizard and check generated values (at last week.)
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today() - relativedelta(days=7),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        # Expense: $ 6,500.00 (invoiced (2x $ 1,000.00) + (5x $ 900.00) = 2,000.00 $ + 4,500.00 $)
        # Price diff.: $ 900.00 ($ 6,500.00 - (7x $ 800.00) = $ 6,500.00 - $ 5,600.00)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 6500},
            {'account_id': account_receivable.id, 'debit': 6500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 900},
            {'account_id': account_stock_variation.id, 'debit': 900, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 6500, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 6500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 900, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 900},
        ])

        # Use accrued order wizard and check generated values (at yesterday.)
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today() - relativedelta(days=1),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        # Expense: $ 5,500.00 (invoiced (2x $ 1,000.00) + (5x $ 900.00) - received (1x $ 1,000.00) = 2,000.00 $ + 4,500.00 $ - $ 1,000.00)
        # Price diff.: $ 700.00 ($ 5,500.00 - (6x $ 800.00) = $ 5,500.00 - $ 4,800.00)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 5500},
            {'account_id': account_receivable.id, 'debit': 5500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 700},
            {'account_id': account_stock_variation.id, 'debit': 700, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 5500, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 5500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 700, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 700},
        ])

        # Use accrued order wizard and check generated values (at today.)
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        # Expense: $ 3,500.00 (invoiced (2x $ 1,000.00) + (5x $ 900.00) - received (3x $ 1,000.00) = 2,000.00 $ + 4,500.00 $ - $ 3,000.00)
        # Price diff.: $ 300.00 ($ 3,500.00 - (4x $ 800.00) = $ 3,500.00 - $ 3,200.00)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 3500},
            {'account_id': account_receivable.id, 'debit': 3500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 300},
            {'account_id': account_stock_variation.id, 'debit': 300, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_expense.id, 'debit': 3500, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 3500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 300, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 300},
        ])
