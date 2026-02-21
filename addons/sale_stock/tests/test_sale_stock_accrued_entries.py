# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun.api import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestAccruedStockSaleOrders(TestSaleCommon):
    def _make_in_move(self,
            product,
            quantity,
            unit_cost=None,
        ):
        """ Helper to create and validate a receipt move.

        :param product: Product to move
        :param quantity: Quantity to move
        :param unit_cost: Price unit
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        receipt_type = warehouse.in_type_id
        product_qty = quantity
        move_vals = {
            'product_id': product.id,
            'location_id': receipt_type.default_location_src_id.id,
            'location_dest_id': receipt_type.default_location_dest_id.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'picking_type_id': receipt_type.id,
        }
        if unit_cost:
            move_vals['value_manual'] = unit_cost * product_qty
            move_vals['price_unit'] = unit_cost
        else:
            move_vals['value_manual'] = product.standard_price * product_qty

        in_move = self.env['stock.move'].create(move_vals)
        in_move._action_confirm()
        in_move._action_assign()
        in_move.picked = True
        in_move._action_done()

        return in_move

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        product = cls.env['product.product'].create({
            'name': "Product",
            'list_price': 30.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
            'invoice_policy': 'delivery',
        })
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                    'tax_ids': False,
                })
            ]
        })
        cls.sale_order.action_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']

    def test_sale_stock_accruals(self):
        # deliver 2 on 2020-01-02
        pick = self.sale_order.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()
        wiz_act = pick.button_validate()
        Form.from_action(self.env, wiz_act).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # deliver 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
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
            {'account_id': self.account_revenue.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
        ])

        # 5 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 150, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 150},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 150},
            {'account_id': wizard.account_id.id, 'debit': 150, 'credit': 0},
        ])

    def test_sale_stock_invoiced_accrued_entries(self):
        # deliver 2 on 2020-01-02
        pick = self.sale_order.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # invoice on 2020-01-04
        inv = self.sale_order._create_invoices()
        inv.invoice_date = fields.Date.to_date('2020-01-04')
        inv.action_post()

        # deliver 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        # invoice on 2020-01-08
        inv = self.sale_order._create_invoices()
        inv.invoice_date = fields.Date.to_date('2020-01-08')
        inv.action_post()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-02',
        })
        # 2 to invoice on 2020-01-07
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
        ])

        # nothing to invoice on 2020-01-05
        wizard.date = fields.Date.to_date('2020-01-05')
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 3 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 90, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 90},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 90},
            {'account_id': wizard.account_id.id, 'debit': 90, 'credit': 0},
        ])

        # nothing to invoice on 2020-01-09
        wizard.date = fields.Date.to_date('2020-01-09')
        with self.assertRaises(UserError):
            wizard.create_entries()

    def test_accrued_order_in_anglo_saxon_standard_perpetual(self):
        """ Ensure the COGS accrual lines are correctly computed."""
        # Create a product using anglox-saxon valuation.
        product_category = self.env['product.category'].create({
            'name': 'Test Category',
            'property_account_income_categ_id': self.account_revenue.id,
            'property_account_expense_categ_id': self.account_expense.id,
            'property_valuation': 'real_time',
        })
        account_variation = product_category.property_stock_valuation_account_id.account_stock_variation_id
        anglo_saxon_product = self.env['product.product'].create({
            'name': "Saxy Product",
            'categ_id': product_category.id,
            'invoice_policy': 'order',
            'is_storable': True,
            'list_price': 120,
            'standard_price': 80,
            'uom_id': self.uom_unit.id,
        })

        # Case 1.: SO with more delivered quantities than invoiced quantities.
        sale_order_1 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': anglo_saxon_product.id,
                    'product_uom_qty': 1,
                    'price_unit': 135,  # Must be different than standard cost.
                    'tax_ids': False,
                })
            ]
        })
        sale_order_1.action_confirm()
        sale_order_1.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        sale_order_1.picking_ids.button_validate()
        # Use accrued order wizard and check generated values.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order_1.id],
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_move = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_move.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 135},
            {'account_id': self.account_expense.id, 'debit': 135, 'credit': 0},
            {'account_id': account_variation.id, 'debit': 0, 'credit': 80},
            {'account_id': self.account_expense.id, 'debit': 80, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 135, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 135},
            {'account_id': account_variation.id, 'debit': 80, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 80},
        ])

        # Case 2.: SO with more invoiced quantities than delivered quantities.
        sale_order_2 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': anglo_saxon_product.id,
                    'product_uom_qty': 1,
                    'tax_ids': False,
                })
            ]
        })
        sale_order_2.action_confirm()
        invoice = sale_order_2._create_invoices()
        invoice.line_ids.price_unit = 140  # Must be different than SO line unit cost.
        invoice.action_post()
        # Use accrued order wizard and check generated values.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order_2.id],
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_move = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_move.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 140, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 140},
            {'account_id': account_variation.id, 'debit': 80, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 80},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 140},
            {'account_id': self.account_expense.id, 'debit': 140, 'credit': 0},
            {'account_id': account_variation.id, 'debit': 0, 'credit': 80},
            {'account_id': self.account_expense.id, 'debit': 80, 'credit': 0},
        ])

    def test_accrued_order_in_anglo_saxon_avco_perpetual(self):
        """ Ensure the COGS accrual lines are correctly computed for AVCO costing method product."""
        # Create a product using anglox-saxon valuation.
        product_category = self.env['product.category'].create({
            'name': 'Test AVCO Category',
            'property_account_income_categ_id': self.account_revenue.id,
            'property_account_expense_categ_id': self.account_expense.id,
            'property_valuation': 'real_time',
            'property_cost_method': 'average',
        })
        account_variation = product_category.property_stock_valuation_account_id.account_stock_variation_id
        # Set the product in the past so its `product.value` won't be considered as the most recent one.
        with freeze_time(fields.Datetime.now() - timedelta(seconds=10)):
            avco_product = self.env['product.product'].create({
                'name': "AVCO Product",
                'categ_id': product_category.id,
                'invoice_policy': 'order',
                'is_storable': True,
                'standard_price': 0,
                'uom_id': self.uom_unit.id,
            })
        self._make_in_move(avco_product, 10, 10)
        self._make_in_move(avco_product, 10, 20)

        # Create a SO for 10 units, deliver 7 units and invoice 5 units.
        sale_order_1 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': avco_product.id,
                    'product_uom_qty': 10,
                    'price_unit': 35,
                    'tax_ids': False,
                })
            ]
        })
        sale_order_1.action_confirm()
        # Deliver 7 / 10 units.
        sale_order_1.picking_ids.move_ids.write({'quantity': 5, 'picked': True})
        backorder_wizard = Form.from_action(self.env, sale_order_1.picking_ids.button_validate())
        backorder_wizard.save().process()
        backorder_delivery = sale_order_1.picking_ids.filtered(lambda pick: pick.state == 'assigned')
        backorder_delivery.move_ids.write({'quantity': 2, 'picked': True})
        backorder_wizard = Form.from_action(self.env, sale_order_1.picking_ids.button_validate())
        backorder_wizard.save().process()
        # Invoice 5 / 10 units.
        invoice = sale_order_1._create_invoices()
        invoice.line_ids.quantity = 5
        invoice.action_post()
        # Use accrued order wizard and check generated values.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order_1.id],
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_move = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_move.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 70},
            {'account_id': self.account_expense.id, 'debit': 70, 'credit': 0},
            {'account_id': account_variation.id, 'debit': 0, 'credit': 30},
            {'account_id': self.account_expense.id, 'debit': 30, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 70, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 70},
            {'account_id': account_variation.id, 'debit': 30, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 30},
        ])

    def test_accrued_order_in_anglo_saxon_fifo_perpetual(self):
        """ Ensure the COGS accrual lines are correctly computed for FIFO costing method product."""
        # Create a product using anglox-saxon valuation.
        product_category = self.env['product.category'].create({
            'name': 'Test FIFO Category',
            'property_account_income_categ_id': self.account_revenue.id,
            'property_account_expense_categ_id': self.account_expense.id,
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
        })
        account_variation = product_category.property_stock_valuation_account_id.account_stock_variation_id
        fifo_product = self.env['product.product'].create({
            'name': "FIFO Product",
            'categ_id': product_category.id,
            'invoice_policy': 'order',
            'is_storable': True,
            'standard_price': 15,
            'uom_id': self.uom_unit.id,
        })
        self._make_in_move(fifo_product, 10, 10)
        self._make_in_move(fifo_product, 10, 20)

        # Create a SO for 10 units, deliver 7 units and invoice 5 units.
        sale_order_1 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': fifo_product.id,
                    'product_uom_qty': 20,
                    'price_unit': 30,
                    'tax_ids': False,
                })
            ]
        })
        sale_order_1.action_confirm()
        # Deliver 17 / 20 units.
        sale_order_1.picking_ids.move_ids.write({'quantity': 17, 'picked': True})
        backorder_wizard = Form.from_action(self.env, sale_order_1.picking_ids.button_validate())
        backorder_wizard.save().process()
        # Invoice 5 / 20 units.
        invoice = sale_order_1._create_invoices()
        invoice.line_ids.quantity = 5
        invoice.line_ids.price_unit = 30
        invoice.action_post()
        # Use accrued order wizard and check generated values.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order_1.id],
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_move = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_move.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 360},
            {'account_id': self.account_expense.id, 'debit': 360, 'credit': 0},
            {'account_id': account_variation.id, 'debit': 0, 'credit': 169.41},
            {'account_id': self.account_expense.id, 'debit': 169.41, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 360, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 360},
            {'account_id': account_variation.id, 'debit': 169.41, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 169.41},
        ])

        # Delivery 3 more units (20 / 20 units.)
        backorder_delivery = sale_order_1.picking_ids.filtered(lambda pick: pick.state == 'assigned')
        backorder_delivery.button_validate()

        # Use accrued order wizard and check generated values.
        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order_1.id],
        }).create({
            'account_id': self.account_expense.id,
            'date': fields.Date.today(),
        })
        account_move_domain = wizard.create_entries()['domain']
        account_move = self.env['account.move'].search(account_move_domain)
        self.assertRecordValues(account_move.line_ids.sorted('id'), [
            # Accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 450},
            {'account_id': self.account_expense.id, 'debit': 450, 'credit': 0},
            {'account_id': account_variation.id, 'debit': 0, 'credit': 229.41},
            {'account_id': self.account_expense.id, 'debit': 229.41, 'credit': 0},
            # Reversal of accrued revenues entries.
            {'account_id': self.account_revenue.id, 'debit': 450, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 450},
            {'account_id': account_variation.id, 'debit': 229.41, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 229.41},
        ])
