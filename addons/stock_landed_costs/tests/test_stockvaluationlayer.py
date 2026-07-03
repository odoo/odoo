# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

import time

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from freezegun import freeze_time


class TestStockValuationLCCommon(TestStockLandedCostsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
        })
        cls.productlc1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'service',
            'categ_id': cls.stock_account_product_categ.id,
            'landed_cost_ok': True,
        })

    def setUp(self):
        super().setUp()
        self.days = 0

    def _get_stock_valuation_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.company_data['default_account_stock_valuation'].id),
        ], order='id')

    def _get_payable_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.company_data['default_account_payable'].id),
        ], order='id')

    def _get_expense_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.company_data['default_account_expense'].id),
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

    def _make_in_move(self, product, quantity, unit_cost=None, create_picking=False, product_uom=False):
        """ Helper to create and validate a receipt move through a purchase order.

        The receipt is driven by a purchase order rather than a manual value so that landed costs
        can influence the product valuation.
        """
        unit_cost = unit_cost or product.standard_price
        price_unit = unit_cost
        if product_uom and product_uom != product.uom_id:
            # unit_cost is expressed per the product's own UoM, while the purchase line
            # prices per product_uom; scale it up so the receipt keeps the same value.
            price_unit = unit_cost * product_uom._compute_quantity(1.0, product.uom_id, round=False)
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': quantity,
                'product_uom_id': product_uom.id if product_uom else product.uom_id.id,
                'price_unit': price_unit,
                'tax_ids': [Command.clear()],
            })],
        })
        po.button_confirm()
        receipt = po.picking_ids
        receipt.move_ids.quantity = receipt.move_ids.product_uom_qty
        receipt.button_validate()

        self.days += 1
        return receipt.move_ids

    def _make_out_move(self, product, quantity, force_assign=None, create_picking=False):
        """ Helper to create and validate a delivery move.
        """
        out_move = self.env['stock.move'].create({
            'product_id': product.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': quantity,
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
        })

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': out_move.picking_type_id.id,
                'location_id': out_move.location_id.id,
                'location_dest_id': out_move.location_dest_id.id,
            })
            out_move.write({'picking_id': picking.id})

        out_move._action_confirm()
        out_move._action_assign()
        if force_assign:
            self.env['stock.move.line'].create({
                'move_id': out_move.id,
                'product_id': out_move.product_id.id,
                'product_uom_id': out_move.product_uom.id,
                'location_id': out_move.location_id.id,
                'location_dest_id': out_move.location_dest_id.id,
            })
        out_move.move_line_ids.quantity = quantity
        out_move.picked = True
        out_move._action_done()

        self.days += 1
        return out_move


@tagged('-at_install', 'post_install')
class TestStockValuationLCFIFO(TestStockValuationLCCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        cls.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_normal_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        lc = self._make_lc(move1, 100)
        move3 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.total_value, 380)
        self.assertEqual(self.product1.qty_available, 19)
        self.assertEqual(self.product1.standard_price, 20)

    def test_negative_1(self):
        # Set the product value prior to the moves so it is applied when their value is computed.
        with freeze_time('2020-01-01'):
            self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15, create_picking=True)
        lc = self._make_lc(move2, 100)

        self.assertEqual(self.product1.total_value, 200)
        self.assertEqual(self.product1.qty_available, 8)

    def test_alreadyout_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.total_value, 0)
        self.assertEqual(self.product1.qty_available, 0)

    def test_alreadyout_2(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move2 = self._make_out_move(self.product1, 1)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.total_value, 380)
        self.assertEqual(self.product1.qty_available, 19)

    def test_alreadyout_3(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        move1.move_line_ids.quantity = 15
        lc = self._make_lc(move1, 60)

        self.assertEqual(self.product1.total_value, 70)
        self.assertEqual(self.product1.qty_available, 5)

    def test_fifo_to_standard_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15)
        move3 = self._make_out_move(self.product1, 5)
        lc = self._make_lc(move1, 100)
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'

        self.assertEqual(self.product1.total_value, 250)
        self.assertEqual(self.product1.qty_available, 15)

    def test_rounding_1(self):
        """Receive (3@20 + 40 landed cost) = 100, then out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=20, create_picking=True)
        lc = self._make_lc(move1, 40)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(move1.value, 100.0)
        for move in (move2, move3, move4):
            self.assertAlmostEqual(move.value, 33.33, delta=0.01)
        self.assertEqual(self.product1.total_value, 0)
        self.assertEqual(self.product1.qty_available, 0)

    def test_rounding_2(self):
        """"Receive (3@20 + 38 landed cost) = 98, then out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=20, create_picking=True)
        lc = self._make_lc(move1, 38)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(move1.value, 98.0)
        for move in (move2, move3, move4):
            self.assertAlmostEqual(move.value, 32.67, delta=0.01)
        self.assertEqual(self.product1.total_value, 0)
        self.assertEqual(self.product1.qty_available, 0)

    def test_rounding_3(self):
        """Receive (3@1 + 1.85 landed cost) = 4.85, out 1, out 1, out 1"""
        move1 = self._make_in_move(self.product1, 3, unit_cost=1, create_picking=True)
        lc = self._make_lc(move1, 1.85)
        move2 = self._make_out_move(self.product1, 1)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_out_move(self.product1, 1)

        self.assertEqual(move1.value, 4.85)
        for move in (move2, move3, move4):
            self.assertAlmostEqual(move.value, 1.62, delta=0.01)
        self.assertEqual(self.product1.total_value, 0)
        self.assertEqual(self.product1.qty_available, 0)

    def test_in_and_out_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=100, create_picking=True)
        self.assertEqual(move1.remaining_value, 1000)
        lc1 = self._make_lc(move1, 100)
        self.assertEqual(move1.remaining_value, 1100)
        lc2 = self._make_lc(move1, 50)
        self.assertEqual(move1.remaining_value, 1150)
        self.assertEqual(self.product1.total_value, 1150)
        self.assertEqual(self.product1.qty_available, 10)
        move2 = self._make_out_move(self.product1, 1)
        self.assertEqual(move2.value, 115)

    def test_landed_cost_different_uom(self):
        """
        Check that the receipt value is correctly updated with the landed cost when the receipt
        uses a different unit of measure than the product's.
        """
        uom_gram = self.env.ref('uom.product_uom_gram')
        uom_kgm = self.env.ref('uom.product_uom_kgm')
        # the product uom is in gram but the transfer is in kg
        self.product1.uom_id = uom_gram
        move1 = self._make_in_move(self.product1, 1, unit_cost=10, create_picking=True, product_uom=uom_kgm)
        self.assertEqual(move1.remaining_value, 10000)
        self.assertEqual(move1.remaining_qty, 1000)
        self._make_lc(move1, 250)
        self.assertEqual(move1.remaining_value, 10250)


@tagged('-at_install', 'post_install')
class TestStockValuationLCAVCO(TestStockValuationLCCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        cls.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_normal_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        lc = self._make_lc(move1, 100)
        move3 = self._make_out_move(self.product1, 1)

        self.assertEqual(self.product1.total_value, 380)

    def test_negative_1(self):
        # Set the product value prior to the moves so it is applied when their value is computed.
        with freeze_time('2020-01-01'):
            self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15, create_picking=True)
        lc = self._make_lc(move2, 100)

        self.assertEqual(self.product1.total_value, 200)
        self.assertEqual(self.product1.qty_available, 8)

    def test_alreadyout_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_out_move(self.product1, 10)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.total_value, 0)
        self.assertEqual(self.product1.qty_available, 0)

    def test_alreadyout_2(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move2 = self._make_out_move(self.product1, 1)
        lc = self._make_lc(move1, 100)

        self.assertEqual(self.product1.total_value, 380)
        self.assertEqual(self.product1.qty_available, 19)

    def test_lc_generated_from_bill_multi_comapnies(self):
        """
        In a multi-company environment:
        Confirm PO, receive products, post bill and generate LC
        """
        company = self.env.company
        self.env.user.company_id = self.env['res.company'].create({
            'name': 'Another Company',
        })

        po_form = Form(self.env['purchase.order'])
        po_form.company_id = company
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10
            po_line.tax_ids.clear()
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        bill_form = Form.from_action(self.env, po.action_create_invoice())
        bill_form.invoice_date = bill_form.date
        with bill_form.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 5
            inv_line.is_landed_costs_line = True
        bill = bill_form.save()
        bill.action_post()

        lc_form = Form.from_action(self.env, bill.button_create_landed_costs())
        lc_form.picking_ids.add(receipt)
        lc = lc_form.save()
        lc.button_validate()

        product = self.product1.with_company(company)
        self.assertEqual(product.total_value, 15)
        self.assertEqual(product.qty_available, 1)
        self.assertEqual(product.standard_price, 15)

@tagged('-at_install', 'post_install')
class TestStockValuationLCFIFOVB(TestStockValuationLCCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationLCFIFOVB, cls).setUpClass()
        cls.vendor1 = cls.env['res.partner'].create({'name': 'vendor1'})
        cls.vendor1.property_account_payable_id = cls.company_data['default_account_payable']
        cls.vendor2 = cls.env['res.partner'].create({'name': 'vendor2'})
        cls.vendor2.property_account_payable_id = cls.company_data['default_account_payable']
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        cls.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

    def test_create_landed_cost_from_bill_multi_currencies(self):
        # create a vendor bill in EUR where base currency in USD
        company = self.env.user.company_id
        currency_grp = self.env.ref('base.group_multi_currency')
        self.env.user.write({'group_ids': [(4, currency_grp.id)]})
        usd_currency = self.env.ref('base.USD')
        eur_currency = self.env.ref('base.EUR')
        eur_currency.active = True

        company.currency_id = usd_currency

        invoice_date = '2023-01-01'
        accounting_date = '2024-01-31'

        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': invoice_date,
            'rate': 1.0,
            'currency_id': usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': invoice_date,
            'rate': 0.5,
            'currency_id': eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': accounting_date,
            'rate': 0.25,
            'currency_id': eur_currency.id,
            'company_id': company.id,
        })

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor1
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        action = po.action_create_invoice()
        bill = self.env['account.move'].browse(action['res_id'])
        bill_form = Form(bill)
        bill_form.invoice_date = invoice_date
        bill_form.date = accounting_date
        bill_form.currency_id = eur_currency

        with bill_form.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 5
            inv_line.currency_id = eur_currency

        bill = bill_form.save()
        bill.action_post()

        lc_form = Form.from_action(self.env, bill.button_create_landed_costs())
        lc_form.picking_ids.add(receipt)
        lc = lc_form.save()
        lc.button_validate()

        self.assertEqual(lc.cost_lines.price_unit, 10)

    def test_vendor_bill_flow_anglo_saxon_1(self):
        """Receiving goods, billing them, then billing a landed cost on its own vendor
        bill and applying it to the receipt capitalises the landed cost into the
        inventory value and posts the expected stock-valuation and expense accounting.
        """
        self.env.company.anglo_saxon_accounting = True

        # Receive 10 @ 10 through a purchase order and bill the received goods.
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [Command.create({
                'product_id': self.product1.id,
                'product_qty': 10,
                'price_unit': 10,
                'tax_ids': [Command.clear()],
            })],
        })
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.quantity = 10
        receipt.button_validate()

        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = fields.Date.today()
        bill.action_post()

        # Bill a landed cost of 50 on its own vendor bill and apply it to the receipt.
        lc_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor2.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.productlc1.id,
                'price_unit': 50,
                'is_landed_costs_line': True,
                'tax_ids': [Command.clear()],
            })],
        })
        lc_bill.action_post()

        lc_form = Form.from_action(self.env, lc_bill.button_create_landed_costs())
        lc_form.picking_ids.add(receipt)
        lc = lc_form.save()
        lc.button_validate()

        self.assertRecordValues(lc.cost_lines, [
            {'product_id': self.productlc1.id, 'price_unit': 50},
        ])
        # The landed cost is capitalised into the inventory value.
        self.assertRecordValues(self.product1, [
            {'total_value': 150, 'qty_available': 10, 'standard_price': 15},
        ])

        # The goods bill debits stock valuation for 100, the landed cost adds 50, and
        # the landed-cost expense is capitalised back out (net expense 0).
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 150)
        self.assertEqual(sum(self._get_expense_move_lines().mapped('balance')), 0)
        self.assertEqual(sum(self._get_payable_move_lines().mapped('balance')), -150)

    def test_vendor_bill_flow_continental_1(self):
        """In continental accounting, receiving goods, billing them, then billing a
        landed cost on its own vendor bill and applying it to the receipt capitalises
        the landed cost into the inventory value and posts the expected stock-valuation
        and expense accounting.
        """
        self.env.company.anglo_saxon_accounting = False

        # Receive 10 @ 10 through a purchase order and bill the received goods.
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor1.id,
            'order_line': [Command.create({
                'product_id': self.product1.id,
                'product_qty': 10,
                'price_unit': 10,
                'tax_ids': [Command.clear()],
            })],
        })
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.quantity = 10
        receipt.button_validate()

        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = fields.Date.today()
        bill.action_post()

        # Bill a landed cost of 50 on its own vendor bill and apply it to the receipt.
        lc_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor2.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.productlc1.id,
                'price_unit': 50,
                'is_landed_costs_line': True,
                'tax_ids': [Command.clear()],
            })],
        })
        lc_bill.action_post()

        lc_form = Form.from_action(self.env, lc_bill.button_create_landed_costs())
        lc_form.picking_ids.add(receipt)
        lc = lc_form.save()
        lc.button_validate()

        self.assertRecordValues(lc.cost_lines, [
            {'product_id': self.productlc1.id, 'price_unit': 50},
        ])
        # The landed cost is capitalised into the inventory value.
        self.assertRecordValues(self.product1, [
            {'total_value': 150, 'qty_available': 10, 'standard_price': 15},
        ])

        # The goods bill debits stock valuation for 100, the landed cost adds 50, and
        # the landed-cost expense is capitalised back out (net expense 0).
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 150)
        self.assertEqual(sum(self._get_expense_move_lines().mapped('balance')), 0)
        self.assertEqual(sum(self._get_payable_move_lines().mapped('balance')), -150)


@tagged('-at_install', 'post_install')
class TestAccountInvoicingWithCOA(TestStockValuationLCCommon):
    def setUp(self):
        super().setUp()
        self.usd = self.env.ref('base.USD')
        self.eur = self.env.ref('base.EUR')
        self.env.company.currency_id = self.usd
        self.env['res.currency.rate'].search([]).unlink()

    def create_rate(self, inv_rate):
        return self.env['res.currency.rate'].create({
            'name': time.strftime('%Y-%m-%d'),
            'inverse_company_rate': inv_rate,
            'currency_id': self.eur.id,
            'company_id': self.env.company.id,
        })

    def _bill(self, po, qty=None, price=None):
        action = po.action_create_invoice()
        bill = self.env['account.move'].browse(action['res_id'])
        bill.invoice_date = fields.Date.today()
        if qty is not None:
            bill.invoice_line_ids.quantity = qty
        if price is not None:
            bill.invoice_line_ids.price_unit = price
        bill.action_post()
        return bill

    def _return(self, picking, qty):
        wizard_form = Form(self.env['stock.return.picking'].with_context(active_ids=picking.ids, active_id=picking.id, active_model='stock.picking'))
        wizard = wizard_form.save()
        wizard.product_return_moves.quantity = qty
        return_picking = wizard._create_return()
        return_picking.move_ids.quantity = qty
        return_picking.button_validate()
        return return_picking

    def _purchase_receipt(self, product, qty, price, curr):
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.env['res.partner'].browse(self.supplier_id)
        po_form.currency_id = curr
        with po_form.order_line.new() as po_line:
            po_line.product_id = product
            po_line.product_qty = qty
            po_line.price_unit = price
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.quantity = qty
        receipt.button_validate()

        return po, receipt

    def test_fifo_return_twice_and_bill_with_landed_cost_and_multi_currency(self):
        """A landed cost applied to a receipt that is returned and returned
        again must not cause the later vendor bill to post a spurious cost of
        goods sold line: the bill only records the goods, the tax and the
        payable.
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.eur.active = True

        with freeze_time('2025-01-01'):
            self.create_rate(1.0)
            po1, _ = self._purchase_receipt(self.product1, 5, 10, self.eur)
            self._bill(po1)

        with freeze_time('2025-01-02'):
            self.create_rate(1.5)
            po2, receipt02 = self._purchase_receipt(self.product1, 10, 10, self.eur)
            self._make_lc(receipt02.move_ids, 10)
            receipt_return = self._return(receipt02, 10)
            self._return(receipt_return, 10)

        with freeze_time('2025-01-03'):
            self.create_rate(2.0)
            bill2 = self._bill(po2)

        valuation_acc_id = self.company_data['default_account_stock_valuation'].id
        tax_acc_id = self.company_data['default_account_tax_purchase'].id
        payable_acc_id = self.company_data['default_account_payable'].id
        self.assertRecordValues(bill2.line_ids, [
            {'account_id': valuation_acc_id, 'balance': 200.0, 'amount_currency': 100},
            {'account_id': tax_acc_id, 'balance': 30.0, 'amount_currency': 15},
            {'account_id': payable_acc_id, 'balance': -230.0, 'amount_currency': -115},
        ])
