# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from freezegun import freeze_time
from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleDataHttpCommon):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.other_currency = self.setup_other_currency('GBP')
        self.product_awesome_item.write({'list_price': 500, 'taxes_id': [(6, 0, self.tax_10_include.ids)]})
        self.product_awesome_article.write({'list_price': 300, 'taxes_id': [(6, 0, self.tax_10_include.ids)]})
        self.product_awesome_thing.write({'list_price': 100, 'taxes_id': [(6, 0, self.tax_10_include.ids)]})

    def compute_tax(self, product, price, qty=1, taxes=None):
        if not taxes:
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id)
        currency = self.pos_config.currency_id
        res = taxes.compute_all(price, currency, qty, product=product)
        untax = res['total_excluded']
        return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

    def _create_pos_order_for_postponed_invoicing(self):
        # Create the order on the first of january.
        with freeze_time('2020-01-01'):
            product = self.env['product.product'].create({
                'name': 'Dummy product',
                'is_storable': True,
                'taxes_id': self.tax_sale_a.ids,
            })
            self.pos_config.open_ui()
            pos_session = self.pos_config.current_session_id
            untax, atax = self.compute_tax(product, 500, 1)
            pos_order_data = {
                'amount_paid': untax + atax,
                'amount_return': 0,
                'amount_tax': atax,
                'amount_total': untax + atax,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'fiscal_position_id': False,
                'lines': [(0, 0, {
                    'discount': 0,
                    'id': 42,
                    'pack_lot_ids': [],
                    'price_unit': 500.0,
                    'product_id': product.id,
                    'price_subtotal': 500.0,
                    'price_subtotal_incl': 575.0,
                    'qty': 1,
                    'tax_ids': [(6, 0, product.taxes_id.ids)]
                })],
                'partner_id': False,
                'session_id': pos_session.id,
                'payment_ids': [(0, 0, {
                    'amount': untax + atax,
                    'name': fields.Datetime.now(),
                    'payment_method_id': self.cash_payment_method.id
                })],
                'last_order_preparation_change': '{}',
                'user_id': self.env.uid
            }
            pos_order_id = self.env['pos.order'].sync_from_ui([pos_order_data])['pos.order'][0]['id']
            pos_order = self.env['pos.order'].browse(pos_order_id)
            # End the session. The order has been created without any invoice.
            self.pos_config.current_session_id.action_pos_session_closing_control()
        return pos_order

    def test_refund_multiple_payment_rounding(self):
        """This test makes sure that the refund amount always correspond to what has been paid in the original order.
           In this example we have a rounding, so we pay 55 in bank that is not rounded, then we pay the rest in cash
           that is rounded. This sum up to 130 paid, so the refund should be 130."""
        self.product_awesome_item.write({'list_price': 134.3})
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding down',
            'rounding': 5.0,
            'rounding_method': 'DOWN',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })
        self.pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.pos_config.open_ui()
        order = self.create_order([{
            'product_id': self.product_awesome_item.product_variant_id,
            'qty': 1,
            'price_unit': 134.38,
            'discount': 0
        }], [
            {'payment_method_id': self.bank_payment_method, 'amount': 130},
        ])
        self.assertEqual(order.amount_paid, 130.0)
        self.assertEqual(order.state, 'paid')

        refund_order = self.env['pos.order'].browse(order.refund()['res_id'])
        payment = self.env['pos.make.payment'].with_context(active_id=refund_order.id).create({
            'payment_method_id': self.pos_config.payment_method_ids[0].id,
        })
        self.assertEqual(payment.amount, -130.0)
        payment.check()
        self.assertEqual(refund_order.amount_paid, -130.0)
        self.assertEqual(refund_order.state, 'paid')

    def test_order_partial_refund_rounding(self):
        """ This test ensures that the refund amound of a partial order corresponds to
        the price of the item, without rounding. """
        self.product_awesome_item.write({'list_price': 12})
        self.product_awesome_article.write({'list_price': 16})
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding down',
            'rounding': 5.0,
            'rounding_method': 'DOWN',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })

        self.pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        order = self.create_order([
            {
                'product_id': self.product_awesome_item.product_variant_id,
                'qty': 1,
                'discount': 0
            },
            {
                'product_id': self.product_awesome_article.product_variant_id,
                'qty': 1,
                'discount': 0
            }
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 25},
        ])
        self.assertEqual(order._get_rounded_amount(order.amount_total), order.amount_paid)
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = 0
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, -15.0)

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        self.assertEqual(refund.state, 'paid')
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed')

    def test_order_partial_refund(self):
        """ The purpose of this test is to make a partial refund of a pos order.
        The amount to refund should depend on the article returned and once the
        payment made, the refund order should be marked as paid."""
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.product_awesome_item.write({'list_price': 10})
        self.product_awesome_article.write({'list_price': 15})
        self.product_awesome_thing.write({'list_price': 20})

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 1, 'discount': 0},
            {'product_id': self.product_awesome_thing.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 45},
        ])
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = 0
            with refund_form.lines.edit(1) as line_2:
                line_2.qty = 0
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, -20.0)

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        self.assertEqual(refund.state, 'paid')
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed')

    def test_order_to_picking(self):
        """
            In order to test the Point of Sale in module, I will do three orders from the sale to the payment,
            invoicing + picking, but will only check the picking consistency in the end.

            TODO: Check the negative picking after changing the picking relation to One2many (also for a mixed use case),
            check the quantity, the locations and return picking logic
        """

        # I click on create a new session button
        self.pos_config.open_ui()

        # I create a PoS order with 2 units of PCSC234 at 450 EUR
        # and 3 units of PCSC349 at 300 EUR.
        self.product_awesome_item.write({'list_price': 450})
        self.product_awesome_article.write({'list_price': 300})
        order1 = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 2, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 1800},
        ])
        self.assertEqual(
            order1.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected during payment
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            order1.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            order1.picking_ids[0].move_ids.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        # I create a second order
        order2 = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': -2, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': -3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': -1800},
        ])
        # I check that the order is marked as paid
        self.assertEqual(
            order2.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            order2.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            order2.picking_ids[0].move_ids.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        order3 = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': -2, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 0},
        ])

        # I check that the order is marked as paid
        self.assertEqual(
            order3.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            order3.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            order3.picking_ids[0].move_ids.mapped('state'),
            ['done'],
            'Move Lines should be in done state.'
        )
        # I close the session to generate the journal entries
        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_to_picking02(self):
        """ This test is similar to test_order_to_picking except that this time, there are two products:
            - One tracked by lot
            - One untracked
            - Both are in a sublocation of the main warehouse
        """
        self.product_awesome_item.write({
            'is_storable': True,
            'tracking': 'lot',
        })
        self.product_awesome_article.write({
            'is_storable': True,
        })
        wh_location = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_data['company'].id)],
            limit=1,
        ).lot_stock_id
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': wh_location.id,
        })
        lot = self.env['stock.lot'].create({
            'name': 'SuperLot',
            'product_id': self.product_awesome_item.product_variant_id.id,
        })
        qty = 2
        self.env['stock.quant']._update_available_quantity(
            self.product_awesome_item.product_variant_id, shelf1_location, qty, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(
            self.product_awesome_article.product_variant_id, shelf1_location, qty)

        self.pos_config.open_ui()
        self.pos_config.current_session_id.update_stock_at_closing = False

        for _i in range(qty):
            order  = self.create_order([
                {
                    'product_id': self.product_awesome_item.product_variant_id,
                    'qty': 1,
                    'discount': 0,
                    'pack_lot_ids': [[0, 0, {'lot_name': lot.name}]]
                },
                {'product_id': self.product_awesome_article.product_variant_id, 'qty': 1, 'discount': 0},
            ], [
                {'payment_method_id': self.bank_payment_method, 'amount': 800},
            ])

            self.assertEqual(order.state, 'paid')
            tracked_line = order.picking_ids.move_line_ids.filtered(
                lambda ml: ml.product_id.id == self.product_awesome_item.product_variant_id.id)
            untracked_line = order.picking_ids.move_line_ids - tracked_line
            self.assertEqual(tracked_line.lot_id, lot)
            self.assertFalse(untracked_line.lot_id)
            self.assertEqual(tracked_line.location_id, shelf1_location)
            self.assertEqual(untracked_line.location_id, shelf1_location)

        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_to_payment_currency(self):
        """
            In order to test the Point of Sale in module, I will do a full flow from the sale to the payment and invoicing.
            I will use two products, one with price including a 10% tax, the other one with 5% tax excluded from the price.
            The order will be in a different currency than the company currency.
        """
        # Make sure the company is in USD
        self.env.ref('base.USD').active = True
        self.env.ref('base.EUR').active = True
        self.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [self.env.ref('base.USD').id, self.env.company.id])

        # Demo data are crappy, clean-up the rates
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': self.env.ref('base.EUR').id,
        })

        # make a config that has currency different from the company
        eur_pricelist = self.env['product.pricelist'].create({'name': 'Test EUR Pricelist', 'currency_id': self.env.ref('base.EUR').id})
        sale_journal = self.env['account.journal'].create({
            'name': 'PoS Sale EUR',
            'type': 'sale',
            'code': 'POSE',
            'company_id': self.company.id,
            'sequence': 12,
            'currency_id': self.env.ref('base.EUR').id
        })
        eur_config = self.pos_config.create({
            'name': 'Shop EUR Test',
            'journal_id': sale_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, eur_pricelist.ids)],
            'pricelist_id': eur_pricelist.id,
            'payment_method_ids': [(6, 0, self.bank_payment_method.ids)]
        })

        # I click on create a new session button
        eur_config.open_ui()
        current_session = eur_config.current_session_id

        # I create a PoS order with 2 units of PCSC234 at 450 EUR (Tax Incl)
        # and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.product_awesome_item.write({
            'list_price': 450,
            'taxes_id': [(6, 0, self.tax_10_include.ids)]
        })
        self.product_awesome_article.write({
            'list_price': 300,
            'taxes_id': [(6, 0, self.tax_05_exclude.ids)]
        })
        order_data = self.make_order_data([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 2, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 3, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 1845},
        ])
        order_data['session_id'] = current_session.id
        result = self.env['pos.order'].sync_from_ui([order_data])
        order1 = self.env['pos.order'].browse(result['pos.order'][0]['id'])
        # I check that the total of the order is now equal to (450*2 +
        # 300*3*1.05)*0.95
        self.assertLess(
            abs(order1.amount_total - (450 * 2 + 300 * 3 * 1.05)),
            0.01, 'The order has a wrong total including tax and discounts')

        # I check that the order is marked as paid
        self.assertEqual(order1.state, 'paid', 'Order should be in paid state.')

        # I generate the journal entries
        current_session.action_pos_session_validate()

        # I test that the generated journal entry is attached to the PoS order
        self.assertTrue(current_session.move_id, "Journal entry should have been attached to the session.")

        # Check the amounts
        debit_lines = current_session.move_id.mapped('line_ids.debit')
        credit_lines = current_session.move_id.mapped('line_ids.credit')
        amount_currency_lines = current_session.move_id.mapped('line_ids.amount_currency')
        for a, b in zip(sorted(debit_lines), [0.0, 0.0, 0.0, 0.0, 922.5]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(credit_lines), [0.0, 22.5, 40.91, 409.09, 450]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(amount_currency_lines), [-900, -818.18, -81.82, -45, 1845]):
            self.assertAlmostEqual(a, b)

    def test_order_with_deleted_tax(self):
        # create tax
        dummy_50_perc_tax = self.env['account.tax'].create({
            'name': 'Tax 50%',
            'amount_type': 'percent',
            'amount': 50.0,
            'price_include_override': 'tax_excluded',
        })

        self.product_awesome_item.write({
            'list_price': 10,
            'taxes_id': [(6, 0, dummy_50_perc_tax.ids)]
        })
        # sell product thru pos
        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 15},
        ])

        # delete tax
        dummy_50_perc_tax.unlink()

        total_cash_payment = sum(pos_session.mapped('order_ids.payment_ids').filtered(
            lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        pos_session.post_closing_cash_details(total_cash_payment)

        # close session (should not fail here)
        # We don't call `action_pos_session_closing_control` to force the failed
        # closing which will return the action because the internal rollback call messes
        # with the rollback of the test runner. So instead, we directly call the method
        # that returns the action by specifying the imbalance amount.
        action = pos_session._close_session_action(5.0)
        wizard = self.env['pos.close.session.wizard'].browse(action['res_id'])
        wizard.with_context(action['context']).close_session()

        # check the difference line
        diff_line = pos_session.move_id.line_ids.filtered(lambda line: line.name == 'Difference at closing PoS session')
        self.assertAlmostEqual(diff_line.credit, 5.0, msg="Missing amount of 5.0")

    def test_order_multi_step_route(self):
        """ Test that orders in sessions with "Ship Later" enabled and "Specific Route" set to a
            multi-step (2/3) route can be validated. This config implies multiple picking types
            and multiple move_lines.
        """
        tracked_product = self.env['product.product'].create({
            'name': 'SuperProduct Tracked',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True
        })
        tracked_product_2 = self.env['product.product'].create({
            'name': 'SuperProduct Tracked 2',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True
        })
        tracked_product_2_lot = self.env['stock.lot'].create({
            'name': '80085',
            'product_id': tracked_product_2.id,
        })
        warehouse_id = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_data['company'].id)],
            limit=1,
        )
        stock_location = warehouse_id.lot_stock_id
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': tracked_product_2.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'lot_id': tracked_product_2_lot.id
        }).action_apply_inventory()
        warehouse_id.delivery_steps = 'pick_ship'

        self.pos_config.ship_later = True
        self.pos_config.warehouse_id = warehouse_id
        self.pos_config.route_id = warehouse_id.route_ids[-1]
        self.pos_config.open_ui()
        self.pos_config.current_session_id.update_stock_at_closing = False

        pos_order = self.create_order([
            {
                'product_id': tracked_product,
                'qty': 1,
                'discount': 0,
                'pack_lot_ids': [[0, 0, {'lot_name': '80085'}]]
            }, {
                'product_id': tracked_product_2,
                'qty': 1,
                'discount': 0,
                'pack_lot_ids': [[0, 0, {'lot_name': '80085'}]]
            },
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 2.3},
        ])
        pickings = pos_order.picking_ids
        picking_mls_no_stock = pickings.move_line_ids.filtered(lambda l: l.product_id.id == tracked_product.id)
        picking_mls_stock = pickings.move_line_ids.filtered(lambda l: l.product_id.id == tracked_product_2.id)
        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(len(picking_mls_no_stock), 0)
        self.assertEqual(len(picking_mls_stock), 1)
        self.assertEqual(len(pickings.picking_type_id), 1)

    def test_order_refund_picking(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        current_session.update_stock_at_closing = True
        # I create a new PoS order with 1 line
        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.cash_payment_method, 'amount': 500},
        ], False, False, self.partner_one, True)

        invoice_pdf_content = str(order.account_move._get_invoice_legal_documents('pdf', allow_fallback=True).get('content'))
        self.assertTrue("using Cash" in invoice_pdf_content)

        # I create a refund
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()

        refund.action_pos_order_invoice()
        self.assertEqual(refund.picking_count, 1)

    def test_order_with_different_payments_and_refund(self):
        """
        Test that all the payments are correctly taken into account when the order contains multiple payments and money refund.
        In this example, we create an order with two payments for a product of 750$:
            - one payment of $200 with customer account
            - one payment of $300 with cash
        Then, we refund the order with $10, and check that the amount still due is 200$.
        """
        # sell product thru pos
        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.credit_payment_method, 'amount': 200},
            {'payment_method_id': self.cash_payment_method, 'amount': 300},
        ], False, False, self.partner_one, True)

        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 10,
            'payment_method_id': self.cash_payment_method.id,
        })
        refund_payment.with_context(**payment_context).check()

        #assert account_move amount_residual is 300
        self.assertEqual(order.account_move.amount_residual, 200)

    def test_sale_order_postponed_invoicing(self):
        """ Test the flow of creating an invoice later, after the POS session has been closed and everything has been processed.
        The process should:
           - Create a new misc entry, that will revert part of the POS closing entry.
           - Create the move and associating payment(s) entry, as it would do when closing with invoice.
           - Reconcile the receivable lines from the created misc entry with the ones from the created payment(s)
        """
        # Extra setup for tax tags
        tags = self.env['account.account.tag'].create([
            {
                'name': f"tag{i}",
                'applicability': 'taxes',
                'country_id': self.company_data['company'].country_id.id,
            }
            for i in range(1, 5)
        ])

        self.tax_sale_a.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'base').write({'tag_ids': tags[0].ids})
        self.tax_sale_a.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').write({'tag_ids': tags[1].ids})
        self.tax_sale_a.refund_repartition_line_ids.filtered(lambda l: l.repartition_type == 'base').write({'tag_ids': tags[2].ids})
        self.tax_sale_a.refund_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').write({'tag_ids': tags[3].ids})

        pos_order = self._create_pos_order_for_postponed_invoicing()

        # Check the closing entry.
        closing_entry = pos_order.session_move_id
        self.assertRecordValues(closing_entry.line_ids.sorted(), [
            {'balance': -75.0,      'account_id': self.company_data['default_account_tax_sale'].id,     'tax_ids': [],                  'tax_tag_ids': tags[1].ids, 'tax_tag_invert': True,     'reconciled': False},
            {'balance': -500.0,     'account_id': self.company_data['default_account_revenue'].id,      'tax_ids': self.tax_sale_a.ids, 'tax_tag_ids': tags[0].ids, 'tax_tag_invert': True,     'reconciled': False},
            {'balance': 575.0,      'account_id': self.company_data['default_account_receivable'].id,   'tax_ids': [],                  'tax_tag_ids': [],          'tax_tag_invert': False,    'reconciled': True},
        ])

        # Client is back on the 3rd, asks for an invoice.
        with freeze_time('2020-01-03'):
            pos_order.partner_id = self.partner_one.id
            pos_order.action_pos_order_invoice()

        # Check the reverse moves, one for the closing entry, one for the statement lines.
        reverse_closing_entries = self.env['account.move'].search([
            ('id', '!=', closing_entry.id),
            ('company_id', '=', self.env.company.id),
            ('statement_line_id', '=', False),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
        ])
        self.assertRecordValues(reverse_closing_entries[0].line_ids.sorted(), [
            {'balance': 75.0,       'account_id': self.company_data['default_account_tax_sale'].id,     'tax_ids': [],                  'tax_tag_ids': tags[1].ids, 'tax_tag_invert': True,     'reconciled': False},
            {'balance': 500.0,      'account_id': self.company_data['default_account_revenue'].id,      'tax_ids': self.tax_sale_a.ids, 'tax_tag_ids': tags[0].ids, 'tax_tag_invert': True,     'reconciled': False},
            {'balance': -575.0,     'account_id': self.company_data['default_account_receivable'].id,   'tax_ids': [],                  'tax_tag_ids': [],          'tax_tag_invert': False,    'reconciled': True},
        ])
        self.assertRecordValues(reverse_closing_entries[1].line_ids.sorted(), [
            {'balance': -575.0,     'account_id': self.company_data['default_account_receivable'].id,   'tax_ids': [],                  'tax_tag_ids': [],          'tax_tag_invert': False,    'reconciled': True},
            {'balance': 575.0,      'account_id': self.company_data['default_account_receivable'].id,   'tax_ids': [],                  'tax_tag_ids': [],          'tax_tag_invert': False,    'reconciled': True},
        ])

    def test_sale_order_postponed_invoicing_anglosaxon(self):
        """ Test the flow of creating an invoice later, after the POS session has been closed and everything has been processed
        in the case of anglo-saxon accounting.
        """
        self.env.company.anglo_saxon_accounting = True
        self.env.company.point_of_sale_update_stock_quantities = 'closing'
        pos_order = self._create_pos_order_for_postponed_invoicing()

        with freeze_time('2020-01-03'):
            # We set the partner on the order
            pos_order.partner_id = self.partner_one.id
            pos_order.action_pos_order_invoice()

        picking_ids = pos_order.session_id.picking_ids
        # only one product is leaving stock
        self.assertEqual(sum(picking_ids.move_line_ids.mapped('quantity')), 1)

    def test_order_pos_tax_same_as_company(self):
        """Test that when the default_pos_receivable_account and the partner account_receivable are the same,
            payment are correctly reconciled and the invoice is correctly marked as paid.
        """
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        current_session.company_id.account_default_pos_receivable_account_id = self.partner_one.property_account_receivable_id

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 500},
        ], False, False, self.partner_one, True)

        self.assertEqual(order.account_move.amount_residual, 0)

    def test_order_refund_with_owner(self):
        # open pos session
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # set up product iwith SN tracing and create two lots (1001, 1002)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_data['company'].id)], limit=1)
        stock_location = warehouse.lot_stock_id
        self.product_awesome_item.write({
            'is_storable': True,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_awesome_item.product_variant_id.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'owner_id': self.partner_one.id
        }).action_apply_inventory()

        # create pos order with the two SN created before

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 500},
        ])
        # I create a refund
        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()
        current_session.action_pos_session_closing_control()
        self.assertEqual(refund.picking_ids.move_line_ids_without_package.owner_id.id, order.picking_ids.move_line_ids_without_package.owner_id.id, "The owner of the refund is not the same as the owner of the original order")

    def test_journal_entries_category_without_account(self):
        # Set company's default accounts to false
        self.pos_config.company_id.income_account_id = False
        self.pos_config.company_id.expense_account_id = False
        self.product_awesome_item.product_variant_id.write({
            'is_storable': True,
            'property_account_income_id': False,
            'property_account_expense_id': False,
        })
        account = self.env['account.account'].create({
            'name': 'Account for category without account',
            'code': 'X1111',
        })

        self.pos_config.journal_id.default_account_id = account.id
        #create a new pos order with the product
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.cash_payment_method, 'amount': 500},
        ], False, False, self.partner_one)
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.move_id.line_ids[0].account_id.id, account.id)

    def test_tracked_product_with_owner(self):
        # open pos session
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # set up product iwith SN tracing and create two lots (1001, 1002)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_data['company'].id)], limit=1)
        stock_location = warehouse.lot_stock_id
        self.product_awesome_item.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.product_awesome_item.product_variant_id.id,
        })

        self.env['stock.quant']._update_available_quantity(
            self.product_awesome_item.product_variant_id, stock_location, 1, lot_id=lot1, owner_id=self.partner_one)


        # create pos order with the two SN created before
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0, 'pack_lot_ids': [[0, 0, {'lot_name': '1001'}]]},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 500},
        ])
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.picking_ids.move_line_ids.owner_id.id, self.partner_one.id)

    def test_order_refund_with_invoice(self):
        """This test make sure that credit notes of pos orders are correctly
           linked to the original invoice."""
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.cash_payment_method, 'amount': 500},
        ], False, False, self.partner_one, True)

        refund_id = order.refund()['res_id']
        refund = self.env['pos.order'].browse(refund_id)
        context_payment = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**context_payment).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        refund_payment.with_context(**context_payment).check()
        refund.action_pos_order_invoice()
        #get last invoice created
        current_session.action_pos_session_closing_control()
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        credit_notes = self.env['account.move'].search([('move_type', '=', 'out_refund')], order='id desc', limit=1)
        self.assertEqual(credit_notes.ref, "Reversal of: "+invoices.name)
        self.assertEqual(credit_notes.reversed_entry_id.id, invoices.id)

    def test_multi_exp_account_real_time(self):

        #Create a real time valuation product category
        self.real_time_categ = self.env['product.category'].create({
            'name': 'test category',
            'parent_id': False,
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

        #Create 2 accounts to be used for each product
        self.account1 = self.env['account.account'].create({
            'name': 'Account 1',
            'code': 'AC1',
            'reconcile': True,
            'account_type': 'expense',
        })
        self.account2 = self.env['account.account'].create({
            'name': 'Account 1',
            'code': 'AC2',
            'reconcile': True,
            'account_type': 'expense',
        })

        self.product_awesome_item.write({
            'is_storable': True,
            'categ_id': self.real_time_categ.id,
            'property_account_expense_id': self.account1.id,
            'property_account_income_id': self.account1.id,
        })
        self.product_awesome_article.write({
            'is_storable': True,
            'categ_id': self.real_time_categ.id,
            'property_account_expense_id': self.account2.id,
            'property_account_income_id': self.account2.id,
        })

        #Create an order with the 2 products
        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
            {'product_id': self.product_awesome_article.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 800},
        ], False, False, self.partner_one, True)

        self.pos_config.current_session_id.action_pos_session_closing_control()
        order.picking_ids._action_done()
        self.assertEqual(len(order.account_move.invoice_line_ids), 2)

    def test_no_default_pricelist(self):
        """Should not have default_pricelist if use_pricelist is false."""

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        self.pos_config.write({
            'pricelist_id': pricelist.id,
            'use_pricelist': False,
        })
        self.pos_config.open_ui()
        loaded_data = self.pos_config.current_session_id.load_data([])

        self.assertFalse(loaded_data['pos.config'][0]['pricelist_id'], False)

    def test_order_different_lots(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.product2 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
        })

        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.product2.id,
        })

        quant1 = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'inventory_quantity': 5,
            'location_id': self.stock_location.id,
            'lot_id': lot1.id
        })
        quant1.action_apply_inventory()
        quant2 = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'inventory_quantity': 5,
            'location_id': self.stock_location.id,
            'lot_id': lot2.id
        })
        quant2.action_apply_inventory()

        order = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_one.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product2.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 12,
                'price_subtotal_incl': 12,
                'pack_lot_ids': [
                    [0, 0, {'lot_name': '1001'}],
                ]
            }),
            (0, 0, {
                'name': "OL/0002",
                'product_id': self.product2.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 6,
                'price_subtotal_incl': 6,
                'pack_lot_ids': [
                    [0, 0, {'lot_name': '1002'}],
                ]
            })],
            'pricelist_id': self.pos_config.pricelist_id.id,
            'amount_paid': 18.0,
            'amount_total': 18.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
            'last_order_preparation_change': '{}'
            })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.bank_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(quant2.quantity, 4)
        self.assertEqual(quant1.quantity, 3)

    def test_pos_branch_account(self):
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })

        self.env.cr.precommit.run()

        bank_payment_method = self.bank_payment_method.copy()
        bank_payment_method.company_id = branch.id

        self.pos_config = self.env['pos.config'].with_company(branch).create({
            'name': 'Main',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_journal_id': self.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, bank_payment_method.id)],
        })

        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': bank_payment_method, 'amount': 500},
        ], False, False, self.partner_one, True)
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed', msg='State of current session should be closed.')

    def test_order_unexisting_lots(self):
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'is_storable': True,
            'tracking': 'lot',
        })

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0, 'pack_lot_ids': [[0, 0, {'lot_name': '1001'}]]},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 500},
        ])

        self.pos_config.current_session_id.action_pos_session_closing_control()
        order_lot_id = order.picking_ids.move_line_ids_without_package.lot_id
        self.assertEqual(order_lot_id.name, '1001')
        self.assertTrue(all([quant.lot_id == order_lot_id for quant in self.env['stock.quant'].search(
            [('product_id', '=', self.product_awesome_item.product_variant_id.id)])]))

    def test_pos_creation_in_branch(self):
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })

        self.env["pos.config"].with_company(branch).create({
            "name": "Branch Point of Sale"
        })

    def test_reordering_rules_triggered_closing_pos(self):
        if self.env['ir.module.module']._get('purchase').state != 'installed':
            self.skipTest("Purchase module is required for this test to run")
        vendor = self.env['res.partner'].create({'name': 'Vendor'})
        self.product_awesome_item.product_variant_id.write({
            'lst_price': 1,
            'is_storable': 'True',
            'seller_ids': [(0, 0, {
                'partner_id': vendor.id,
                'min_qty': 1.0,
                'price': 1.0,
            })]
        })

        self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product_awesome_item.product_variant_id.id,
            'location_id': self.pos_config.picking_type_id.default_location_src_id.id,
            'product_min_qty': 1.0,
            'product_max_qty': 1.0,
        })

        self.pos_config.open_ui()

        order = self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 1},
        ])
        self.pos_config.current_session_id.action_pos_session_closing_control()
        purchase_order = self.env['purchase.order'].search([], limit=1)
        self.assertEqual(purchase_order.order_line.product_id.id, self.product_awesome_item.product_variant_id.id)
        self.assertEqual(purchase_order.order_line.product_qty, 2)

    def test_product_combo_creation(self):
        setup_product_combo_items(self)
        """We check that combo products are created without taxes."""
        # Test product combo creation
        product_form = Form(self.env['product.product'])
        product_form.name = "Test Combo Product"
        product_form.lst_price = 100
        product_form.type = "combo"
        product_form.combo_ids = self.desk_accessories_combo
        product = product_form.save()
        self.assertTrue(product.combo_ids)

        product_form.type = "consu"
        product = product_form.save()
        self.assertFalse(product.combo_ids)
