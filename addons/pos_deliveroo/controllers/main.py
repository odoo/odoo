# coding: utf-8
import json
import hmac
import hashlib

from odoo import http, fields
from odoo.http import request
from werkzeug import exceptions

def formatPrice(price):
    cents = {
        "EUR": 2,
    }
    return price['fractional'] / 10**cents[price['currency']]
class PosDeliverooController(http.Controller):
    @http.route('/pos_deliveroo/order', type='json', methods=['POST'], auth='none', csrf=False)
    def notification(self):
        # https://api-docs.deliveroo.com/v2.0/reference/order-events-webhook-1
        data = json.loads(request.httprequest.data)
        pos_delivery_service_sudo = request.env['pos.delivery.service'].sudo().search([])[0]
        # https://api-docs.deliveroo.com/v2.0/docs/securing-webhooks
        expected_signature = hmac.new(bytes(pos_delivery_service_sudo.webhook_secret, 'utf-8'), msg=bytes(f"{request.httprequest.headers.get('X-Deliveroo-Sequence-Guid')} {request.httprequest.data.decode('utf-8')}", 'utf-8'), digestmod=hashlib.sha256).hexdigest()
        if expected_signature != request.httprequest.headers.get('X-Deliveroo-Hmac-Sha256'):
            return exceptions.BadRequest()
        # TODO make sure that the order is not already in the system
        # is_order_duplicate = request.env['pos.order'].sudo().search([('pos_reference', '=', data['pos_reference'])])
        pos_config_sudo = pos_delivery_service_sudo.config_id
        order = data['body']['order']
        # if not pos_config_sudo.has_active_session:
            #TODO: refuse the order
        request.env["pos.order"].sudo().create({
            # TODO: add all the missing fields
            # 'user_id':      ui_order['user_id'] or False,
            'session_id':   pos_config_sudo.current_session_id,
            'sequence_number':pos_config_sudo.current_session_id.sequence_number,
            'pos_reference': request.env['pos.order'].sudo()._generate_unique_id(config_id=pos_config_sudo),
            'lines': [
                (0,0,{
                    'product_id':   line['pos_item_id'],
                    'qty':          line['quantity'],
                    'price_unit':   formatPrice(line['unit_price']),
                    'price_extra':  formatPrice(line['menu_unit_price']) - formatPrice(line['unit_price']), # Price per unit according to the menu (can be different from Unit Price in case of more expensive substitutions, for example)
                    'discount': 0,
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                })
                for line in order['items']
            ],
            # 'partner_id':   False,
            'date_order': str(fields.Datetime.now()),
            'amount_paid':  formatPrice(order['partner_order_total']) - formatPrice(order['cash_due']),
            'amount_total':  formatPrice(order['partner_order_total']),
        })

        # request.env['pos.delivery.service'].sudo().search([('service', '=', 'deliveroo')])._new_order(order_id_sudo)
        # find a way do get the proper domain for the delivery service
        # print(request.env['pos.delivery.service'].sudo().search([('service', '=', 'deliveroo')])._refresh_access_token())
        if data['event'] == 'order.new':
            # ask the preparation dipslay for acceptation
            request.env['pos.delivery.service'].sudo().search([])[0].sudo()._accept_order(data['body']['order']['id'])
        elif data['event'] == 'order.status_update':
            # TODO: in the 'order.status_update' event, deliveroo tells us if they have accepted the order or not
            # we should only start preparing the order if it has been accepted by deliveroo
            pass
        print(data)
        return
