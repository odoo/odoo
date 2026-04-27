from odoo import fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_session_orders(self):
        orders = super().get_session_orders()
        return orders.filtered(lambda order: not order.delivery_datetime or order.state not in ['draft', 'cancel'])
