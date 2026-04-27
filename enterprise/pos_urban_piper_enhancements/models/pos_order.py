from datetime import datetime, timedelta
from odoo import fields, models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    delivery_datetime = fields.Datetime(
        string='Delivery Datetime',
        help='Scheduled delivery datetime for the delivery order.'
    )
    is_notified = fields.Boolean(
        string='Is Notified',
        help='Flag indicating if the delivery notification has been sent.',
    )

    @api.model
    def notify_future_deliveries(self):
        future_orders = self.search([
            ('delivery_datetime', '>', datetime.utcnow()),
            ('is_notified', '=', False)
        ])
        orders_to_notify = self.env['pos.order']
        for order in future_orders:
            delivery_datetime = order.delivery_datetime
            notify_time = delivery_datetime - timedelta(minutes=order.prep_time)
            if datetime.utcnow() >= notify_time:
                orders_to_notify |= order
        if orders_to_notify:
            for order in orders_to_notify:
                if not order.session_id.config_id.current_session_id:
                    order.session_id.config_id.order_status_update(order.id, 'Cancelled', 'store_closed')
                    order.state = 'cancel'
                    continue
                if order.session_id != order.session_id.config_id.current_session_id:
                    order.session_id = order.session_id.config_id.current_session_id
            for config in orders_to_notify.session_id.config_id:
                config[0]._notify('FUTURE_ORDER_NOTIFICATION', orders_to_notify.filtered(lambda o: o.session_id.config_id.id == config.id).ids)
            orders_to_notify.is_notified = True
