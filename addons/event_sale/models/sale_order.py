# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = "sale.order"

    attendee_count = fields.Integer('Attendee Count', compute='_compute_attendee_count')

    def write(self, vals):
        """ Synchronize partner from SO to registrations. This is done notably
        in website_sale controller shop/address that updates customer, but not
        only. """
        result = super(SaleOrder, self).write(vals)
        if any(line.product_type == 'event' for line in self.order_line) and vals.get('partner_id'):
            registrations_toupdate = self.env['event.registration'].sudo().search([('sale_order_id', 'in', self.ids)])
            registrations_toupdate.write({'partner_id': vals['partner_id']})
        return result

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if not any(line.product_type == 'event' for line in so.order_line):
                continue
            so_lines_missing_events = so.order_line.filtered(lambda line: line.product_type == 'event' and not line.event_id)
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
        """Override of `_get_product_catalog_domain` to extend the domain.

        :returns: A list of tuples that represents a domain.
        :rtype: list
        """
        domain = super()._get_product_catalog_domain()
        return expression.AND([domain, [('detailed_type', '!=', 'event')]])
