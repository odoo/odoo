# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    attendee_count = fields.Integer('Attendee Count', compute='_compute_attendee_count')

    def write(self, vals):
        """ Synchronize partner from SO to registrations. This is done notably
        in website_sale controller shop/address that updates customer, but not
        only. """
        result = super(SaleOrder, self).write(vals)
        if vals.get('partner_id'):
            registrations_toupdate = self.sudo().env['event.registration'].search([('sale_order_id', 'in', self.ids)])
            registrations_toupdate.write({'partner_id': vals['partner_id']})
        return result

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if not any(line.product_type == 'event' for line in so.order_line):
                continue
            # confirm registration if it was free (otherwise it will be confirmed once invoice fully paid)
            so.order_line._update_registrations(confirm=so.amount_total == 0, cancel_to_draft=False)
            if len(self) == 1:
                return self.env['ir.actions.act_window'].with_context(
                    default_sale_order_id=so.id
                )._for_xml_id('event_sale.action_sale_order_event_registration')
        return res

    def _action_cancel(self):
        self.order_line._cancel_associated_registrations()
        return super()._action_cancel()

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._for_xml_id("event.event_registration_action_tree")
        action['domain'] = [('sale_order_id', 'in', self.ids)]
        return action

    def _compute_attendee_count(self):
        sale_orders_data = self.env['event.registration']._read_group(
            [('sale_order_id', 'in', self.ids),
             ('state', '!=', 'cancel')],
            ['sale_order_id'], ['sale_order_id']
        )
        attendee_count_data = {
            sale_order_data['sale_order_id'][0]:
            sale_order_data['sale_order_id_count']
            for sale_order_data in sale_orders_data
        }
        for sale_order in self:
            sale_order.attendee_count = attendee_count_data.get(sale_order.id, 0)

    def unlink(self):
        self.order_line._unlink_associated_registrations()
        return super(SaleOrder, self).unlink()
