# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.helpdesk.tests import common
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestHelpdeskStock(common.HelpdeskCommon):
    """ Test used to check that the functionalities of After sale in Helpdesk (stock).
    """

    def test_helpdesk_stock(self):
        # give the test team ability to create coupons
        self.test_team.use_product_returns = True

        product = self.env['product.product'].create({
            'name': 'product 1',
            'is_storable': True,
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
        with stock_picking_form.product_return_moves.edit(0) as line:
            line.quantity = 1
        return_picking = stock_picking_form.save()

        self.assertEqual(len(return_picking.product_return_moves), 1,
            "A picking line should be present")
        self.assertEqual(return_picking.product_return_moves[0].product_id, product,
            "The product of the picking line does not match the product of the sale order")

        return_picking.action_create_returns()

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
            'is_storable': True,
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

    def test_helpdesk_ticket_partner_has_picking(self):
        """
        This test case verifies that a helpdesk ticket correctly identifies if its associated partner
        or the partner's commercial entity has related delivery orders after confirming a sale order.
        """
        product = self.env['product.product'].create({
            'name': 'Product 2',
            'is_storable': True,
            'invoice_policy': 'order',
        })
        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Customer',
            'is_company': True,
        })
        # Create a child partner
        partner = self.env['res.partner'].create({
            'name': 'Customer 2',
            'parent_id': commercial_partner.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'price_unit': 10,
                'product_uom_qty': 5,
            })],
        })
        sale_order.action_confirm()
        delivery_order = sale_order.picking_ids[0]
        delivery_order.move_ids[0].quantity = 5
        delivery_order.button_validate()

        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'partner_id': partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': sale_order.id,
        })

        self.assertTrue(ticket.has_partner_picking,
                        "The ticket should have a related delivery order for the partner.")

        # assign commercial_partner to partner_id in ticket
        ticket.partner_id = commercial_partner

        self.assertTrue(ticket.has_partner_picking,
                        "The ticket should have a related delivery order for the commercial partner")

    def test_helpdesk_ticket_product_from_parent_company(self):
        company_product, employee_1_product, employee_2_product = self.env['product.product'].create([
            {'name': 'Company Product'},
            {'name': 'Employee 1 Product'},
            {'name': 'Employee 2 Product'},
        ])
        partners = self.env['res.partner'].create([
            {'name': 'Company', 'company_type': 'company'},
            {'name': 'Employee 1', 'company_type': 'person'},
            {'name': 'Employee 1', 'company_type': 'person'},
        ])
        company, employee_1, employee_2 = partners
        (employee_1 | employee_2).commercial_partner_id = company

        sale_orders = self.env['sale.order'].create([
            {'partner_id': company.id, 'order_line': [Command.create({'product_id': company_product.id})]},
            {'partner_id': employee_1.id, 'order_line': [Command.create({'product_id': employee_1_product.id})]},
            {'partner_id': employee_2.id, 'order_line': [Command.create({'product_id': employee_2_product.id})]},
        ])
        sale_orders.action_confirm()

        products = (company_product | employee_1_product | employee_2_product)
        ticket = self.env['helpdesk.ticket'].create({'name': 'Ticket'})

        for partner in partners:
            ticket.partner_id = partner
            self.assertEqual(ticket.suitable_product_ids, products, 'Products from all children of the parent company should be visible')

    def test_ensure_has_partner_picking(self):
        """
        It is possible to return some products from a ticket. To do so, the user
        clicks on the Return button. That button will only be displayed in a
        condition strongly based on the field `has_partner_picking` (tldr: the
        client must have an outgoing done picking). This test ensures the field
        value is correct in several cases.
        """
        product, service = self.env['product.product'].create([
            {'name': 'Amazing Product', 'type': 'consu'},
            {'name': 'Amazing Service', 'type': 'service'},
        ])

        partners = self.env['res.partner'].create([{
            'name': name,
        } for name in [
            'No SO',
            'SO with service',
            'Draft SO',
            'Confirmed SO',
            'Cancelled SO',
            'Done SO',
        ]])

        service_sale_order = self.env['sale.order'].create([{
            'partner_id': partners[1].id,
            'order_line': [(0, 0, {'product_id': service.id})]
        }])

        _draft_so, confirmed_so, canceled_so, done_so = self.env['sale.order'].create([{
            'partner_id': partner.id,
            'order_line': [(0, 0, {'product_id': product.id})]
        } for partner in partners[2:]])

        (confirmed_so | canceled_so | done_so | service_sale_order).action_confirm()

        canceled_so.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(canceled_so.state, 'cancel')

        done_so.picking_ids.move_ids.quantity = 1
        done_so.picking_ids.button_validate()
        self.assertEqual(done_so.picking_ids.state, 'done')

        tickets = self.env['helpdesk.ticket'].create([{
            'name': 'Amazing ticket',
            'partner_id': partner.id,
        } for partner in partners])

        done_so_ticket = tickets.filtered(lambda t: t.partner_id == done_so.partner_id)
        other_tickets = tickets - done_so_ticket

        self.assertTrue(done_so_ticket.has_partner_picking)
        self.assertEqual(other_tickets.mapped('has_partner_picking'), [False] * 5)

    def test_set_picking_to_false_in_wizard(self):
        """ This test ensure that when the picking field of the wizard is set to False, no traceback is triggered during
        the product_return_moves compute."""
        product = self.env['product.product'].create({
            'name': 'test product',
            'is_storable': True,
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
        delivery_order = so.picking_ids[0]
        delivery_order.move_ids[0].quantity = 5
        delivery_order.button_validate()

        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': so.id
        })

        wizard_form = Form(self.env['stock.return.picking'].with_context({
            'active_model': 'helpdesk.ticket',
            'default_ticket_id': ticket.id
        }))
        wizard_form.picking_id = self.env['stock.picking']

    def test_return_picking_default_multistep_delivery(self):
        """
        Tests that when returning a product from a helpdesk ticket, the correct
        delivery order is selected by default in multi-step delivery scenarios.
        The default should always be the final customer-facing operation (Ship/Out).
        """

        warehouse = self.env['stock.warehouse'].create({
            'name': 'Multi-Step Test WH',
            'code': 'MSWH',
        })
        product_multi_step = self.env['product.product'].create({
            'name': 'Multi-Step Test Product',
            'is_storable': True,
        })

        routes = ['pick_ship', 'pick_pack_ship']
        for steps in routes:
            with self.subTest(delivery_steps=steps):
                warehouse.write({'delivery_steps': steps})

                so = self.env['sale.order'].create({
                    'partner_id': self.partner.id,
                    'warehouse_id': warehouse.id,
                    'order_line': [Command.create({'product_id': product_multi_step.id, 'product_uom_qty': 1})],
                })
                so.action_confirm()

                final_picking = self.env['stock.picking']
                current_picking = so.picking_ids
                while current_picking:
                    current_picking.move_ids.quantity = 1
                    current_picking.button_validate()
                    final_picking = current_picking
                    current_picking = current_picking.move_ids.move_dest_ids.picking_id

                self.assertEqual(final_picking.state, 'done')

                ticket = self.env['helpdesk.ticket'].create({
                    'name': f'Return for {steps}',
                    'partner_id': self.partner.id,
                    'team_id': self.test_team.id,
                    'sale_order_id': so.id,
                })
                return_wizard_form = Form(self.env['stock.return.picking'].with_context({
                    'active_model': 'helpdesk.ticket',
                    'default_ticket_id': ticket.id,
                }))

                self.assertEqual(
                    return_wizard_form.picking_id,
                    final_picking,
                    f"For {steps} delivery, the final OUT operation should be defaulted."
                )

    def test_copy_ticket_without_stock_user(self):
        service_product = self.env['product.product'].create({
            'name': "Service product",
            'type': 'service',
        })
        ticket_1 = self.env['helpdesk.ticket'].create({
            'name': 'Ticket 1',
            'team_id': self.test_team.id,
            'partner_id': self.partner.id,
            'product_id': service_product.id
        })
        # Copy the ticket using a user who does not have stock access
        copied_ticket = ticket_1.with_user(self.helpdesk_user).copy()
        self.assertFalse(copied_ticket.product_id, 'The duplicated ticket should not retain the product.')
