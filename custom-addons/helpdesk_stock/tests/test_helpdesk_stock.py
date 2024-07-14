# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests import common
from odoo.exceptions import UserError
from odoo.tests.common import Form, tagged


@tagged('post_install', '-at_install')
class TestHelpdeskStock(common.HelpdeskCommon):
    """ Test used to check that the functionalities of After sale in Helpdesk (stock).
    """

    def test_helpdesk_stock(self):
        # give the test team ability to create coupons
        self.test_team.use_product_returns = True

        product = self.env['product.product'].create({
            'name': 'product 1',
            'type': 'product',
            'invoice_policy': 'order',
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'price_unit': 10,
            'product_uom_qty': 1,
            'order_id': so.id,
        })
        so.action_confirm()
        so._create_invoices()
        invoice = so.invoice_ids
        invoice.action_post()
        so.picking_ids[0].move_ids[0].quantity = 1
        so.picking_ids[0].button_validate()
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': self.partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': so.id,
        })

        stock_picking_form = Form(self.env['stock.return.picking'].with_context({
            'active_model': 'helpdesk.ticket',
            'default_ticket_id': ticket.id
        }))
        stock_picking_form.picking_id = so.picking_ids[0]
        return_picking = stock_picking_form.save()

        self.assertEqual(len(return_picking.product_return_moves), 1,
            "A picking line should be present")
        self.assertEqual(return_picking.product_return_moves[0].product_id, product,
            "The product of the picking line does not match the product of the sale order")

        return_picking.create_returns()

        return_picking = self.env['stock.picking'].search([
            ('partner_id', '=', self.partner.id),
            ('picking_type_code', '=', 'incoming'),
        ])

        self.assertEqual(len(return_picking), 1, "No return created")
        self.assertEqual(return_picking.state, 'assigned', "Wrong status of the refund")
        self.assertEqual(ticket.pickings_count, 1,
            "The ticket should be linked to a return")
        self.assertEqual(return_picking.id, ticket.picking_ids[0].id,
            "The correct return should be referenced in the ticket")

        return_picking.move_ids[0].quantity = 1
        return_picking.button_validate()
        # Trigger _compute_state
        return_picking.state

        last_message = str(ticket.message_ids[0].body)

        self.assertTrue(return_picking.display_name in last_message and 'Return' in last_message,
            'Return validation should be logged on the ticket')

    def test_helpdesk_stock_return(self):
        """
        You should be able to return a product that has an open backorder.
        """
        product = self.env['product.product'].create({
            'name': 'test product',
            'type': 'product',
            'invoice_policy': 'order',
        })
        partner = self.env['res.partner'].create({
            'name': 'Customer'
        })
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'price_unit': 10,
            'product_uom_qty': 5,
            'order_id': so.id,
        })
        so.action_confirm()
        # get delivery order
        delivery_order = so.picking_ids[0]
        # validated only 3 units
        delivery_order.move_ids[0].quantity = 3
        # validate delivery order
        delivery_order.button_validate()
        # create backorder with form
        Form(self.env['stock.backorder.confirmation'].with_context({
            'button_validate_picking_ids': [delivery_order.id],
            'default_pick_ids': [(4, delivery_order.id)],
            'default_show_transfers': False,
            'skip_sanity_check': True,
        })).save().process()
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': so.id
        })
        try:
            # create a return picking on ticket
            Form(self.env['stock.return.picking'].with_context({
                'active_model': 'helpdesk.ticket',
                'default_ticket_id': ticket.id
            }))
        except UserError:
            self.fail("We should be able to make a return of the already delivered quantities "
                      "even if the so has an open backorder that isn't done")
