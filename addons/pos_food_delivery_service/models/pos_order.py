from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    delivery_provider_id = fields.Many2one('pos.online.delivery.provider', string='Delivery Provider')
    delivery_id = fields.Char(string='Delivery ID')
    delivery_status = fields.Selection([('awaiting', 'Awaiting'), ('scheduled', 'Scheduled'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('ready', 'Ready'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], string='Delivery Status')
    delivery_note = fields.Text(string='Delivery Note')

    def _export_for_ui(self, order):
        res = super(PosOrder, self)._export_for_ui(order)
        res['delivery_provider_name'] = order.delivery_provider_id.name if order.delivery_provider_id else False
        return res
    
    def accept_delivery_order(self):
        self.ensure_one()
        status_to_send = 'accepted' if self.delivery_status == 'awaiting' else 'confirmed'
        self.delivery_provider_id._accept_order(self.delivery_id, status_to_send)
        # self.env['pos.delivery.service'].search([('config_ids', 'in', self.config_id.id), ('service', 'ilike', self.delivery_service_id.name)])._accept_order(self.delivery_id, status_to_send)
        self._post_delivery_accept_order()

    def _post_delivery_accept_order(self):
        if not self.delivery_asap:
            if self.delivery_status == 'awaiting':
                self.delivery_status = 'scheduled'
            elif self.delivery_status == 'scheduled':
                self.delivery_status = 'confirmed'
        else:
            self.delivery_status = 'preparing'
        self.session_id.config_id._send_delivery_order_count(self.id)

    def reject_delivery_order(self, reject_reason):
        self.ensure_one()
        self.delivery_provider_id._reject_order(self.delivery_id, reject_reason)
        # self.env['pos.delivery.service'].search([('config_ids', 'in', self.config_id.id), ('service', 'ilike', self.delivery_service_id.name)])._reject_order(self.delivery_id, reject_reason)
        self._post_delivery_reject_order()

    def _post_delivery_reject_order(self):
        refund_order = self._refund()
        self.env['pos.payment'].create({
            'pos_order_id': refund_order.id,
            'amount': self.amount_paid,
            'payment_date': self.date_order,
            'payment_method_id': self.payment_ids.payment_method_id.id,
        })
        refund_order.state = 'paid'
        self.delivery_status = 'cancelled'
        self.session_id.config_id._send_delivery_order_count(self.id)

    def change_order_delivery_status(self, new_status):
        self.ensure_one()
        self.delivery_status = new_status
        self.session_id.config_id._send_delivery_order_count(self.id)

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['delivery_id'] = ui_order.get('delivery_id', '')
        res['delivery_status'] = ui_order.get('delivery_status', None)
        return res
    
    def _export_for_ui(self, order):
        res = super(PosOrder, self)._export_for_ui(order)
        res['delivery_id'] = order.delivery_id
        res['delivery_status'] = order.delivery_status
        res['delivery_note'] = order.delivery_note or False
        return res