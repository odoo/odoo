# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    event_booth_ids = fields.One2many('event.booth', 'sale_order_id', string='Booths')
    event_booth_count = fields.Integer(string='Booth Count', compute='_compute_event_booth_count')

    @api.depends('event_booth_ids')
    def _compute_event_booth_count(self):
        slot_data = self.env['event.booth']._read_group(
            [('sale_order_id', 'in', self.ids)],
            ['sale_order_id'], ['__count'],
        )
        slot_mapped = {sale_order.id: count for sale_order, count in slot_data}
        for so in self:
            so.event_booth_count = slot_mapped.get(so.id, 0)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if not any(line.service_tracking == 'event_booth' for line in so.order_line):
                continue
            so_lines_missing_booth = so.order_line.filtered(lambda line: line.service_tracking == 'event_booth' and not line.event_booth_pending_ids)
            if so_lines_missing_booth:
                so_lines_descriptions = "".join(f"\n- {so_line_description.name}" for so_line_description in so_lines_missing_booth)
                raise ValidationError(_("Please make sure all your event-booth related lines are configured before confirming this order:%s", so_lines_descriptions))
            so.order_line._update_event_booths()
        return res

    def action_view_booth_list(self):
        action = self.env['ir.actions.act_window']._for_xml_id('event_booth.event_booth_action')
        action['domain'] = [('sale_order_id', 'in', self.ids)]
        return action

    def _get_product_catalog_domain(self):
        return super()._get_product_catalog_domain() & Domain('service_tracking', '!=', 'event_booth')
