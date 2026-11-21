# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = "sale.order"

    attendee_count = fields.Integer('Attendee Count', compute='_compute_attendee_count')

    def write(self, vals):
        """ Synchronize partner from SO to registrations. This is done notably
        in website_sale controller shop/address that updates customer, but not
        only. """
        result = super(SaleOrder, self).write(vals)
        if any(line.service_tracking == 'event' for line in self.order_line) and vals.get('partner_id'):
            registrations_toupdate = self.env['event.registration'].sudo().search([('sale_order_id', 'in', self.ids)])
            registrations_toupdate.write({'partner_id': vals['partner_id']})
        return result

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for so in self:
            if not any(line.service_tracking == 'event' for line in so.order_line):
                continue
            so_lines_missing_events = so.order_line.filtered(lambda line: line.service_tracking == 'event' and not line.event_id)
            if so_lines_missing_events:
                so_lines_descriptions = "".join(f"\n- {so_line_description.name}" for so_line_description in so_lines_missing_events)
                raise ValidationError(_("Please make sure all your event related lines are configured before confirming this order:%s", so_lines_descriptions))
            # Initialize registrations
            so.order_line._init_registrations()
            if len(self) == 1:
                return self.env['ir.actions.act_window'].with_context(
                    default_sale_order_id=so.id
                )._for_xml_id('event_sale.action_sale_order_event_registration')
        return res

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._for_xml_id("event.event_registration_action_tree")
        action['domain'] = [('sale_order_id', 'in', self.ids)]
        return action

    def _compute_attendee_count(self):
        sale_orders_data = self.env['event.registration']._read_group(
            [('sale_order_id', 'in', self.ids),
             ('state', '!=', 'cancel')],
            ['sale_order_id'], ['__count'],
        )
        attendee_count_data = {
            sale_order.id: count for sale_order, count in sale_orders_data
        }
        for sale_order in self:
            sale_order.attendee_count = attendee_count_data.get(sale_order.id, 0)

    def _get_product_catalog_domain(self):
        return super()._get_product_catalog_domain() & Domain('service_tracking', '!=', 'event')

    def _get_event_ticket_option_registrations(self, ticket_line):
        return self.env['event.registration'].sudo().search([
            ('sale_order_line_id', '=', ticket_line.id),
            ('state', '!=', 'cancel'),
        ], order='create_date asc, id asc')

    def _sync_event_ticket_option_lines(self, ticket_lines):
        """ Make the option lines match what the (non cancelled) attendees of each ticket line
        chose: one option line per (ticket line, product), its quantity being the number of
        attendees who picked the option. """
        self.ensure_one()
        order = self.with_context(event_ticket_option_sync=True)
        for ticket_line in ticket_lines.exists():
            wanted = defaultdict(int)
            for registration in self._get_event_ticket_option_registrations(ticket_line):
                for product in registration.ticket_option_product_ids:
                    wanted[product.id] += 1

            option_lines = ticket_line.linked_line_ids.filtered('is_event_ticket_option')
            for line in option_lines:
                quantity = wanted.pop(line.product_id.id, 0)
                if not quantity and self.state in ('draft', 'sent'):
                    line.unlink()
                elif quantity != line.product_uom_qty:
                    # a confirmed order keeps its lines: a quantity of 0 removes the option
                    line.product_uom_qty = quantity
            products = self.env['product.product'].browse(wanted)
            for product in products:
                order._create_event_ticket_option_line(ticket_line, product, wanted[product.id])

    def _create_event_ticket_option_line(self, ticket_line, product, quantity):
        """ Add the option line of a ticket line; overridden to go through the cart on websites. """
        self.ensure_one()
        return self.env['sale.order.line'].create({
            'order_id': self.id,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'linked_line_id': ticket_line.id,
            'is_event_ticket_option': True,
        })
