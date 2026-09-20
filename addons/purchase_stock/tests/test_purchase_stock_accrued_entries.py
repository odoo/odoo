from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseStock(AccountTestInvoicingCommon):

    _test_user_groups = None

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
                    'uom_id': product.uom_id.id,
                    'price_unit': product.list_price,
                    'tax_ids': False,
                }),
            ]
        })
        cls.purchase_order.button_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']

    def test_purchase_stock_accruals(self):
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({
            'quantity': 2,
            'picked': True,
        })
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
            'default_accrual_type': 'bill_to_receive',
        }).create({
            'account_id': self.account_expense.id,
            'date': '2020-01-01',
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        wizard.date = fields.Date.to_date('2020-01-04')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 150},
            {'account_id': wizard.account_id.id, 'debit': 150, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 150, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 150},
        ])

    def test_purchase_stock_invoiced_accrued_entries(self):
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-04')
        move.action_post()

        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-08')
        move.action_post()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
            'default_accrual_type': 'billed_not_received',
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-02',
        })

        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        wizard.date = fields.Date.to_date('2020-01-05')
        with self.assertRaises(UserError):
            wizard.create_entries()

        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 90},
            {'account_id': wizard.account_id.id, 'debit': 90, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 90, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 90},
        ])

        wizard.date = fields.Date.to_date('2020-01-09')
        with self.assertRaises(UserError):
            wizard.create_entries()

    @freeze_time('2025-07-01')
    def test_purchase_stock_accruals_anglo_saxon_price_diff(self):
        """ Accrued entries for the price difference between standard cost and invoiced/received price. """
        def _create_invoice_for_po(purchase_order, date):
            with freeze_time(date):
                action_view_invoice = purchase_order.action_create_invoice()
                action_view_invoice['context'].update(default_purchase_id=purchase_order.id, default_date=date)
                move_form = Form.from_action(self.env, action_view_invoice)
                move_form.invoice_date = date
                move_form.move_type = 'in_invoice'
                move_form.partner_id = self.partner_a
                return move_form.save()

        account_receivable = self.company_data['default_account_receivable']
        account_stock_variation = self.product_a.categ_id.account_stock_variation_id
        stock_price_diff_acc_id = self.env['account.account'].create({
            'name': 'default_account_stock_price_diff',
            'code': 'STOCKDIFF',
            'account_type': 'asset_current',
        })
        self.product_a.categ_id.update({
            'property_valuation': 'real_time',
            'property_price_difference_account_id': stock_price_diff_acc_id.id,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'uom_id': self.product_a.uom_id.id,
                    'price_unit': self.product_a.list_price,
                    'tax_ids': False,
                }),
            ]
        })
        purchase_order.button_confirm()
        invoice_1 = _create_invoice_for_po(purchase_order, '2025-04-01')
        invoice_1.line_ids[0].quantity = 2
        invoice_1.action_post()
        invoice_2 = _create_invoice_for_po(purchase_order, '2025-06-01')
        invoice_2.line_ids[0].quantity = 5
        invoice_2.line_ids[0].price_unit = 900.00
        invoice_2.action_post()
        with freeze_time('2025-06-30'):
            receipt_1 = purchase_order.picking_ids
            receipt_1.move_ids.update({'quantity': 1, 'picked': True})
            wizard_create_backorder = Form.from_action(self.env, receipt_1.button_validate()).save()
            wizard_create_backorder.process()
        receipt_2 = purchase_order.picking_ids[-1]
        receipt_2.move_ids.update({'quantity': 2, 'picked': True})
        wizard_create_backorder = Form.from_action(self.env, receipt_2.button_validate()).save()
        wizard_create_backorder.process()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
            'default_accrual_type': 'billed_not_received',
        }).create({
            'account_id': account_receivable.id,
            'date': '2025-05-31',
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 2000},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 400},
            {'account_id': account_stock_variation.id, 'debit': 400, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 2000, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 2000, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 400, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 400},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 2000},
        ])

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
            'default_accrual_type': 'billed_not_received',
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today() - relativedelta(days=7),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 6500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 900},
            {'account_id': account_stock_variation.id, 'debit': 900, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 6500, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 6500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 900, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 900},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 6500},
        ])

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
            'default_accrual_type': 'billed_not_received',
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today() - relativedelta(days=1),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 5500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 700},
            {'account_id': account_stock_variation.id, 'debit': 700, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 5500, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 5500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 700, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 700},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 5500},
        ])

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
            'default_accrual_type': 'billed_not_received',
        }).create({
            'account_id': account_receivable.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_moves = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_moves.line_ids.sorted('id'), [
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 3500},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 0, 'credit': 300},
            {'account_id': account_stock_variation.id, 'debit': 300, 'credit': 0},
            {'account_id': account_receivable.id, 'debit': 3500, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 3500, 'credit': 0},
            {'account_id': stock_price_diff_acc_id.id, 'debit': 300, 'credit': 0},
            {'account_id': account_stock_variation.id, 'debit': 0, 'credit': 300},
            {'account_id': account_receivable.id, 'debit': 0, 'credit': 3500},
        ])

    def test_purchase_stock_accruals_ordered_quantities_no_receipt(self):
        """ Nothing is accrued for a storable, ordered-quantity-controlled product not yet received. """
        self.purchase_order.order_line.product_id.update({
            'is_storable': True,
            'purchase_method': 'purchase',
        })
        self.assertFalse(self.purchase_order.order_line.amount_to_invoice_at_date)
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
            'default_accrual_type': 'bill_to_receive',
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.context_today(self),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()


@tagged('post_install', '-at_install')
class TestAccruedPurchaseOrdersStock(AccountTestInvoicingCommon):
    """ `purchase`'s accrued-orders tests for storable products (need `stock`). """

    def _create_accrual_product(self, storable, real_time):
        category = self.env['product.category'].create({
            'name': 'Real Time Category' if real_time else 'Periodic Category',
            'property_valuation': 'real_time' if real_time else 'periodic',
            'property_cost_method': 'average',
        })
        return self.env['product.product'].create({
            'name': 'Storable Product' if storable else 'Non-stock Product',
            'type': 'consu',
            'is_storable': storable,
            'categ_id': category.id,
            'standard_price': 100.0,
        })

    def _create_purchase_order(self, product, qty, price_unit, fulfill=False):
        """ `fulfill=True` also fully receives and bills the PO on the spot. """
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_qty': qty,
                'price_unit': price_unit,
                'tax_ids': False,
            })],
        })
        purchase_order.button_confirm()
        if fulfill:
            self._set_qty_received(purchase_order, qty)
            self._create_bill(purchase_order)
        return purchase_order

    def _set_qty_received(self, purchase_order, qty):
        """ Receive `qty` on `purchase_order`, via its receipt picking for a storable product. """
        pickings = purchase_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        if not pickings:
            purchase_order.order_line.qty_received = qty
            return
        pickings.move_ids.quantity = qty
        pickings.with_context(skip_backorder=True).button_validate()

    def _create_bill(self, purchase_order, invoice_date=False):
        move = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = invoice_date or fields.Date.today()
        move.action_post()
        return move

    def _cancel_accrual_entries(self, moves):
        moves.filtered(lambda m: m.state == 'posted').button_draft()
        moves.unlink()

    def _filter_reversal(self, moves):
        """ `moves.line_ids` without the scheduled reversal move's lines. """
        return moves.filtered(lambda m: not m.reversed_entry_id).line_ids

    def _get_accrual_lines(self, report_data):
        """ `report_data['accrual']['lines']` flattened to (type, account, debit, credit). """
        return [
            {'accrual_type': line['accrual_type'], 'account_id': sub_line['account_id'], 'debit': sub_line['debit'], 'credit': sub_line['credit']}
            for line in report_data['accrual']['lines'] if 'accrual_type' in line
            for sub_line in line['lines']
        ]

    def test_bill_to_receive(self):
        """ "Bills to Receive" accrual for a non-stock-tracked product. """
        product = self._create_accrual_product(storable=False, real_time=False)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['bills_to_receive']
        expense_account = product.product_tmpl_id._get_product_accounts()['expense']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'bill_to_receive',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._set_qty_received(purchase_order, 5)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertNotIn('accrual', report_data)
        self.assertFalse(report_data["stock_variation"]["lines"])

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': expense_account.id, 'debit': 500, 'credit': 0},
            {'account_id': accrual_account.id, 'debit': 0, 'credit': 500},
        ])

        self._cancel_accrual_entries(account_move)
        with self.assertRaises(UserError):
            self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)

    def test_billed_not_received(self):
        """ "Billed Not Received" accrual for a non-stock-tracked product. """
        product = self._create_accrual_product(storable=False, real_time=False)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        product.purchase_method = 'purchase'
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['billed_not_received']
        expense_account = product.product_tmpl_id._get_product_accounts()['expense']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'billed_not_received',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._create_bill(purchase_order)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertNotIn('accrual', report_data)
        self.assertFalse(report_data["stock_variation"]["lines"])

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': expense_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': accrual_account.id, 'debit': 1000, 'credit': 0},
        ])

        self._cancel_accrual_entries(account_move)
        with self.assertRaises(UserError):
            self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)

    def test_bill_to_receive_realtime(self):
        """ Same as `test_bill_to_receive`, for a storable, real-time-valued product. """
        product = self._create_accrual_product(storable=True, real_time=True)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['bills_to_receive']
        stock_valuation_account = product.product_tmpl_id._get_product_accounts()['stock_valuation']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'bill_to_receive',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._set_qty_received(purchase_order, 5)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertEqual(self._get_accrual_lines(report_data), [{
            'accrual_type': 'bills_to_receive',
            'account_id': accrual_account.id,
            'debit': 0,
            'credit': 500.0,
        }])
        self.assertEqual(report_data['ending_stock']['lines_by_account_id'][stock_valuation_account.id], {'value': 2500.0})
        self.assertFalse(report_data['stock_variation']['lines'])

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': stock_valuation_account.id, 'debit': 500, 'credit': 0},
            {'account_id': accrual_account.id, 'debit': 0, 'credit': 500},
        ])

        self._cancel_accrual_entries(account_move)
        action = self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)
        moves = self.env['account.move'].search(action['domain'])
        self.assertRecordValues(self._filter_reversal(moves), [
            {'account_id': stock_valuation_account.id, 'debit': 500, 'credit': 0},
            {'account_id': accrual_account.id, 'debit': 0, 'credit': 500},
        ])

    def test_billed_not_received_realtime(self):
        """ Same as `test_billed_not_received`, for a storable, real-time-valued product. """
        product = self._create_accrual_product(storable=True, real_time=True)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        product.purchase_method = 'purchase'
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['billed_not_received']
        stock_valuation_account = product.product_tmpl_id._get_product_accounts()['stock_valuation']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'billed_not_received',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._create_bill(purchase_order)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertEqual(self._get_accrual_lines(report_data), [{
            'accrual_type': 'billed_not_received',
            'account_id': accrual_account.id,
            'debit': 1000.0,
            'credit': 0,
        }])
        self.assertEqual(report_data['ending_stock']['lines_by_account_id'][stock_valuation_account.id], {'value': 2000.0})
        self.assertFalse(report_data['stock_variation']['lines'])

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': stock_valuation_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': accrual_account.id, 'debit': 1000, 'credit': 0},
        ])

        self._cancel_accrual_entries(account_move)
        action = self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)
        moves = self.env['account.move'].search(action['domain'])
        self.assertRecordValues(self._filter_reversal(moves), [
            {'account_id': stock_valuation_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': accrual_account.id, 'debit': 1000, 'credit': 0},
        ])

    def test_bill_to_receive_periodic(self):
        """ Same as `test_bill_to_receive`, for a storable, periodic-valued product. """
        product = self._create_accrual_product(storable=True, real_time=False)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['bills_to_receive']
        stock_valuation_account = product.product_tmpl_id._get_product_accounts()['stock_valuation']
        stock_variation_account = product.product_tmpl_id._get_product_accounts()['stock_variation']
        expense_account = product.product_tmpl_id._get_product_accounts()['expense']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'bill_to_receive',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._set_qty_received(purchase_order, 5)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertNotIn('accrual', report_data)
        self.assertEqual(report_data['ending_stock']['lines_by_account_id'][stock_valuation_account.id], {'value': 2500.0})
        self.assertNotIn(stock_variation_account.id, report_data['ending_stock']['lines_by_account_id'])
        self.assertEqual(report_data['stock_variation']['lines'], [
            {'account_id': stock_variation_account.id, 'debit': 0, 'credit': 2500.0},
            {'account_id': stock_valuation_account.id, 'debit': 2500.0, 'credit': 0},
        ])
        self.assertEqual(report_data['ending_stock']['value'], 2500.0)

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': expense_account.id, 'debit': 500, 'credit': 0},
            {'account_id': accrual_account.id, 'debit': 0, 'credit': 500},
        ])

        self._cancel_accrual_entries(account_move)
        action = self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)
        moves = self.env['account.move'].search(action['domain']).filtered(lambda m: not m.reversed_entry_id)
        accrual_move = moves.filtered(lambda m: accrual_account in m.line_ids.account_id)
        closing_move = moves.filtered(lambda m: stock_variation_account in m.line_ids.account_id)
        self.assertEqual(len(moves), 2)
        self.assertRecordValues(accrual_move.line_ids, [
            {'account_id': expense_account.id, 'debit': 500, 'credit': 0},
            {'account_id': accrual_account.id, 'debit': 0, 'credit': 500},
        ])
        self.assertRecordValues(closing_move.line_ids, [
            {'account_id': stock_variation_account.id, 'debit': 0, 'credit': 2500},
            {'account_id': stock_valuation_account.id, 'debit': 2500, 'credit': 0},
        ])

    def test_billed_not_received_periodic(self):
        """ Same as `test_billed_not_received`, for a storable, periodic-valued product. """
        product = self._create_accrual_product(storable=True, real_time=False)
        self._create_purchase_order(product, qty=10.0, price_unit=200.0, fulfill=True)
        product.purchase_method = 'purchase'
        purchase_order = self._create_purchase_order(product, qty=10.0, price_unit=100.0)
        accrual_account = product.product_tmpl_id._get_product_accounts()['billed_not_received']
        stock_valuation_account = product.product_tmpl_id._get_product_accounts()['stock_valuation']
        stock_variation_account = product.product_tmpl_id._get_product_accounts()['stock_variation']
        expense_account = product.product_tmpl_id._get_product_accounts()['expense']

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order.line',
            'active_ids': purchase_order.order_line.ids,
            'default_accrual_type': 'billed_not_received',
        }).create({
            'date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.create_entries()

        self._create_bill(purchase_order)

        report_data = self.env['account.stock.valuation.report'].with_company(self.env.company)._get_report_data()
        self.assertNotIn('accrual', report_data)
        self.assertEqual(report_data['ending_stock']['lines_by_account_id'][stock_valuation_account.id], {'value': 2000.0})
        self.assertEqual(report_data['stock_variation']['lines'], [
            {'account_id': stock_variation_account.id, 'debit': 0, 'credit': 2000.0},
            {'account_id': stock_valuation_account.id, 'debit': 2000.0, 'credit': 0},
        ])
        self.assertEqual(report_data["ending_stock"]["value"], 2000.0)

        account_move = self.env['account.move'].search(wizard.create_entries()['domain'])
        self.assertRecordValues(self._filter_reversal(account_move), [
            {'account_id': expense_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': accrual_account.id, 'debit': 1000, 'credit': 0},
        ])

        self._cancel_accrual_entries(account_move)
        action = self.env.company.action_close_stock_valuation(auto_post=True, include_accruals=True)
        moves = self.env['account.move'].search(action['domain']).filtered(lambda m: not m.reversed_entry_id)
        accrual_move = moves.filtered(lambda m: accrual_account in m.line_ids.account_id)
        closing_move = moves.filtered(lambda m: stock_variation_account in m.line_ids.account_id)
        self.assertEqual(len(moves), 2)
        self.assertRecordValues(
            accrual_move.line_ids,
            [
                {"account_id": expense_account.id, "debit": 0, "credit": 1000},
                {"account_id": accrual_account.id, "debit": 1000, "credit": 0},
            ],
        )
        self.assertRecordValues(closing_move.line_ids, [
            {'account_id': stock_variation_account.id, 'debit': 0, 'credit': 2000},
            {'account_id': stock_valuation_account.id, 'debit': 2000, 'credit': 0},
        ])
