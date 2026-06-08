from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if registrations := self.mapped('lines.event_registration_ids'):
            registrations._update_available_seat()
        return res
