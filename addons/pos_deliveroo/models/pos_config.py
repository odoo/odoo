from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_delivery_order_count(self):
        res = super().get_delivery_order_count()
        res['deliveroo'] = self.get_deliveroo_order_count()
        return res

    def get_deliveroo_order_count(self):
        if not self.current_session_id:
            return {
                'awaiting': 0,
                'preparing': 0,
            }
        order_count = {
            'awaiting': self.env['pos.order'].search_count([('session_id', '=', self.current_session_id.id), ('delivery_id', '!=', False), ('delivery_status', '=', 'awaiting')]),
            'scheduled': self.env['pos.order'].search_count([('session_id', '=', self.current_session_id.id), ('delivery_id', '!=', False), ('delivery_status', 'in', ['scheduled', 'confirmed'])]),
            'preparing': self.env['pos.order'].search_count([('session_id', '=', self.current_session_id.id), ('delivery_id', '!=', False), ('delivery_status', '=', 'preparing')]),
        }
        return order_count
