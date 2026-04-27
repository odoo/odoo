# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestHelpdeskStockAccount(HelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # give the test team ability to return and refund products
        cls.test_team.use_product_returns = True
        cls.test_team.use_credit_notes = True
        cls.journal_id = cls.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', cls.main_company_id)], limit=1).id
        cls.product = cls.env['product.product'].create({
            'name': 'Test product',
            'is_storable': True,
            'invoice_policy': 'order',
        })
        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': cls.partner.id,
            'team_id': cls.test_team.id,
        })

    def test_refund_after_return_single_so(self):
        """ When we refund a storable product, the product that weren't returned shouldn't be part of the refund """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5,
            })],
        })
        sale_order.action_confirm()
        sale_order._create_invoices()
        sale_order.invoice_ids.action_post()  # confirm invoice
        sale_order.picking_ids.move_ids.quantity = 5
        sale_order.picking_ids.button_validate()  # confirm delivery
        self.return_product(sale_order, 2)  # return 2 products
        refund_move = self.refund_product(sale_order.invoice_ids)  # create a refund for the invoice
        self.assertEqual(refund_move.invoice_line_ids.quantity, 2)

    def test_refund_after_return_multi_so(self):
        """ Same test as before, but this time with multiple sales orders """
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': self.partner.id,
                'order_line': [Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 10,
                })],
            },
            {
                'partner_id': self.partner.id,
                'order_line': [Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 5,
                })],
            },
        ])
        sale_orders.action_confirm()
        sale_orders._create_invoices()
        sale_orders.invoice_ids.action_post()  # confirm invoice
        sale_orders[0].picking_ids.move_ids.quantity = 10
        sale_orders[1].picking_ids.move_ids.quantity = 5
        sale_orders.picking_ids.button_validate()  # confirm deliveries
        self.return_product(sale_orders[0], 2)  # return 2 products from so1
        self.return_product(sale_orders[1], 3)  # return 3 products from so1
        refund_move = self.refund_product(sale_orders.invoice_ids)  # create a refund for the invoice
        self.assertEqual(refund_move.invoice_line_ids[0].quantity, 2)
        self.assertEqual(refund_move.invoice_line_ids[1].quantity, 3)

    def test_refund_after_return_down_payment(self):
        """ Same test as before, but this time by refunding a product on multiple invoices (down payment) """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5,
            })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.quantity = 5
        sale_order.picking_ids.button_validate()  # confirm delivery
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment.create_invoices()
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({})
        payment.create_invoices()
        self.return_product(sale_order, 2)  # return 2 products
        refund_moves = self.refund_product(sale_order.invoice_ids)  # create a refund for the invoice
        product_line = refund_moves[0].invoice_line_ids[0]
        down_payment_line = refund_moves[0].invoice_line_ids[2]
        self.assertEqual(product_line.quantity, -8)  # since it is a down payment, the qty is 10 - 2
        self.assertEqual(down_payment_line.quantity, 1)  # down payment qty shouldn't change

    def refund_product(self, invoice):
        credit_note = self.env['account.move.reversal'].create({
            'helpdesk_ticket_id': self.ticket.id,
            'journal_id': self.journal_id,
            'reason': 'test',
            'move_ids': invoice,
            'product_id': self.product.id,
        })
        res = credit_note.refund_moves()
        return self.env['account.move'].browse(res.get('res_id') or res['domain'][0][2])

    def return_product(self, sale_order, qty):
        stock_picking_return = self.env['stock.return.picking'].create({
            'picking_id': sale_order.picking_ids.id,
        })
        stock_picking_return.product_return_moves.quantity = qty
        return_picking = stock_picking_return._create_return()
        return_picking.move_ids.quantity = qty
        return_picking.button_validate()
        Form(self.env['stock.backorder.confirmation'].with_context({
            'button_validate_picking_ids': [return_picking.id],
            'default_pick_ids': [(4, return_picking.id)],
            'default_show_transfers': False,
            'skip_sanity_check': True,
        })).save().process()  # return product

        return return_picking

    def test_refund_only_one_product(self):
        """
        This test verifies that a refund of only one product is created if a product has been selected, in the case
        of a corresponding invoice containing several products.
        Test case:
            - Create a SO with 2 products
            - Confirm SO and create invoice
            - Confirm invoice
            - Create helpdesk Ticket
            - In the refund wizard, select a product
            - Create a credit note
            - Check if the only product selected is present on the credit note
        """
        product_0 = self.env['product.product'].create({
            'name': 'Test Product 0',
            'list_price': 10,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 5,
                }),
                Command.create({
                    'product_id': product_0.id,
                    'product_uom_qty': 5,
                })],
            })

        sale_order.action_confirm()
        sale_order._create_invoices()
        invoice = sale_order.invoice_ids
        invoice.action_post()
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': self.partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': sale_order.id,
        })
        credit_note = self.env['account.move.reversal'].create({
            'helpdesk_ticket_id': ticket.id,
            'journal_id': self.journal_id,
            'reason': 'test',
            'move_ids': invoice,
            'product_id': self.product.id,
        })
        credit_note.refund_moves()
        self.assertEqual(credit_note.new_move_ids.invoice_line_ids.product_id, self.product)

    def test_refund_with_product_as_helpdesk_user(self):
        """ Ensure a non-stock user can create a refund from a helpdesk ticket."""
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 5,
                }),
            ],
        })
        sale_order.action_confirm()
        sale_order._create_invoices()
        sale_order.invoice_ids.action_post()
        self.ticket.write({
            'sale_order_id': sale_order.id,
        })
        self.helpdesk_user.groups_id += self.env.ref('account.group_account_invoice')
        credit_note_form = Form(self.env['account.move.reversal'].with_user(self.helpdesk_user).with_context({'default_helpdesk_ticket_id': self.ticket.id}),
            view=self.env.ref('helpdesk_account.view_account_move_reversal_inherit_helpdesk_account')
        )
        credit_note = credit_note_form.save()  # Should not raise AccessError
        res = credit_note.reverse_moves()
        refund = self.env['account.move'].browse(res['res_id'])
        self.assertTrue(refund)
