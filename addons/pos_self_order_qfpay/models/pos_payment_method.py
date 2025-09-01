# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields
from odoo.fields import Domain


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        if config.self_ordering_mode == 'kiosk':
            domain = Domain.OR([[('use_payment_terminal', '=', 'qfpay'), ('id', 'in', config.payment_method_ids.ids)], domain])
        return domain

    @api.model
    def _qfpay_handle_webhook(self, config, data, uuid):
        if config.self_ordering_mode != 'kiosk':
            return super()._qfpay_handle_webhook(config, data, uuid)

        if data.get('notify_type') != 'payment':
            return

        if data['status'] == "1":
            order = self.env['pos.order'].search([('uuid', '=', uuid)], limit=1)
            if order:
                order.add_payment({
                    'amount': order.amount_total,
                    'payment_date': fields.Datetime.now(),
                    'payment_method_id': self.id,
                    'payment_ref_no': data['chnlsn'],
                    'transaction_id': data['syssn'],
                    'pos_order_id': order.id,
                })
                order.action_pos_order_paid()

                order._send_payment_result("Success")
        else:
            order._send_payment_result("fail")
