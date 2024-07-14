# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Repair(models.Model):
    _inherit = 'repair.order'

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket", help="Related Helpdesk Ticket")

    def write(self, vals):
        previous_states = None
        if 'state' in vals:
            previous_states = {repair: repair.state for repair in self}
        res = super().write(vals)
        if 'state' in vals:
            tracked_repairs = self.filtered(
                lambda r: r.ticket_id.use_product_repairs and r.state in ('done', 'cancel') and previous_states[r] != r.state)
            for repair in tracked_repairs:
                subtype = self.env.ref('helpdesk.mt_ticket_repair_status', raise_if_not_found=False)
                if not subtype:
                    continue
                state_desc = dict(self._fields['state']._description_selection(self.env))[repair.state].lower()
                body = repair._get_html_link() + f" {_('Repair')} {state_desc}"
                repair.ticket_id.sudo().message_post(subtype_id=subtype.id, body=body)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        message = _('Repair Created')
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        for order in orders.filtered('ticket_id'):
            order.message_post_with_source(
                'helpdesk.ticket_creation',
                render_values={'self': order, 'ticket': order.ticket_id},
                subtype_id=subtype_id
            )
            order.ticket_id.message_post_with_source(
                'helpdesk.ticket_conversion_link',
                render_values={'created_record': order, 'message': message},
                subtype_id=subtype_id,
            )
        return orders

    def _action_repair_confirm(self):
        """repair.action_repair_confirm() apply changes on move_ids which,
        if default_lot_id is still in the context, will give all stock_move_lines.lot_id this value.
        We want to avoid that, as the components of the repair do not have the same lot_id, if any,
        so it leads to an exception.
        """
        context = dict(self.env.context)
        context.pop('default_lot_id', None)
        return super(Repair, self.with_context(context))._action_repair_confirm()
