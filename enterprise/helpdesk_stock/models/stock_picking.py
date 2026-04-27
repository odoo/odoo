# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_state(self):
        # Since `state` is a computed field, it does not go through the `write` function we usually use to track
        # those changes.
        previous_states = {picking: picking.state for picking in self}
        res = super()._compute_state()
        tracked_pickings = self.filtered(lambda m: m.state in ('done', 'cancel') and\
            m.state != previous_states[m])
        ticket_ids = self.env['helpdesk.ticket'].sudo().search([
            ('use_product_returns', '=', True), ('picking_ids', 'in', tracked_pickings.ids)])
        if ticket_ids:
            mapped_data = dict()
            for ticket in ticket_ids:
                mapped_data[ticket] = (ticket.picking_ids & self)
            for ticket, pickings in mapped_data.items():
                if not pickings:
                    continue
                subtype = self.env.ref('helpdesk.mt_ticket_return_status', raise_if_not_found=False)
                if not subtype:
                    continue
                state_desc = dict(self._fields['state']._description_selection(self.env))[pickings[0].state].lower()
                body = Markup('<br/>').join(
                    picking._get_html_link() + self.env._('Return %(status)s', status=state_desc)
                    for picking in pickings
                )
                ticket.message_post(subtype_id=subtype.id, body=body)
        return res
