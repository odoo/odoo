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
    return price['fractional'] / 10**cents[price['currency_code']]
class PosDeliverooController(http.Controller):
    #ORDER API
    @http.route('/pos_deliveroo/order', type='json', methods=['POST'], auth='none', csrf=False)
    def notification(self):
        # https://api-docs.deliveroo.com/v2.0/reference/order-events-webhook-1
        data = json.loads(request.httprequest.data)
        signature = request.httprequest.headers.get('X-Deliveroo-Hmac-Sha256')
        deliveroo_providers_sudo = request.env['pos.online.delivery.provider'].sudo().search([('code', '=', 'deliveroo')])
        deliveroo_provider = False
        for deliveroo_provider_sudo in deliveroo_providers_sudo:
            expected_signature = hmac.new(bytes(deliveroo_provider_sudo.webhook_secret, 'utf-8'), msg=bytes(f"{request.httprequest.headers.get('X-Deliveroo-Sequence-Guid')} {request.httprequest.data.decode('utf-8')}", 'utf-8'), digestmod=hashlib.sha256).hexdigest()
            if expected_signature == signature:
                deliveroo_provider = deliveroo_provider_sudo
                break
        if not deliveroo_provider:
            return exceptions.BadRequest()
        # pos_delivery_service_sudo = request.env['pos.delivery.service'].sudo().search([])[0]
        # https://api-docs.deliveroo.com/v2.0/docs/securing-webhooks
        # expected_signature = hmac.new(bytes(pos_delivery_service_sudo.webhook_secret, 'utf-8'), msg=bytes(f"{request.httprequest.headers.get('X-Deliveroo-Sequence-Guid')} {request.httprequest.data.decode('utf-8')}", 'utf-8'), digestmod=hashlib.sha256).hexdigest()
        # if expected_signature != request.httprequest.headers.get('X-Deliveroo-Hmac-Sha256'):
        #     return exceptions.BadRequest()
        # TODO make sure that the order is not already in the system
        # is_order_duplicate = request.env['pos.order'].sudo().search([('pos_reference', '=', data['pos_reference'])])
        pos_config_sudo = deliveroo_provider.config_ids[0]
        order = data['body']['order']
        if order['status'] == 'canceled' or not pos_config_sudo.has_active_session:
            request.env['pos.delivery.service'].sudo().search([])[0].sudo()._reject_order(order['id'], "closing_early")
        if order['status'] == 'canceled':
            pos_order = request.env['pos.order'].sudo().search([('delivery_id', '=', order['id'])])
            if pos_order:
                pos_order._post_delivery_reject_order()
        if not request.env['pos.order'].sudo().search([('delivery_id', '=', order['id'])]):
            order_prepare_for = order['prepare_for'].replace('T', ' ')[:-1]
            notes = ''
            amount_paid = formatPrice(order['partner_order_total']) - formatPrice(order['cash_due'])
            date_order = str(fields.Datetime.now())
            if order['order_notes']:
                notes += order['order_notes']
            if order['cutlery_notes']:
                if notes:
                    notes += '\n'
                notes += order['cutlery_notes']
            delivery_order = request.env["pos.order"].sudo().create({
                # TODO: add all the missing fields
                'delivery_id': order['id'],
                'delivery_status': 'awaiting',
                'delivery_display': order['display_id'],
                'delivery_provider_id': deliveroo_provider.id,
                'delivery_asap': order['asap'],
                'delivery_confirm_at': order['confirm_at'].replace('T', ' ')[:-1],
                'delivery_start_preparing_at': order['start_preparing_at'].replace('T', ' ')[:-1],
                'delivery_prepare_for': order_prepare_for,
                'company_id': pos_config_sudo.current_session_id.company_id.id,
                'session_id':   pos_config_sudo.current_session_id.id,
                'sequence_number':pos_config_sudo.current_session_id.sequence_number,
                'pos_reference': request.env['pos.order'].sudo()._generate_unique_id(config_id=pos_config_sudo, prefix="Deliveroo"),
                # the creation of lines should be more precise (taxes and other fields)
                'lines': [
                    (0,0,{
                        'product_id':   int(line['pos_item_id']),
                        'qty':          line['quantity'],
                        'price_unit':   formatPrice(line['unit_price']),
                        'price_extra':  formatPrice(line['menu_unit_price']) - formatPrice(line['unit_price']), # Price per unit according to the menu (can be different from Unit Price in case of more expensive substitutions, for example)
                        'discount': 0,
                        'price_subtotal': formatPrice(line['menu_unit_price']) * line['quantity'],
                        'price_subtotal_incl': formatPrice(line['menu_unit_price']) * line['quantity'],
                    })
                    for line in order['items']
                ],
                # should take into account the "child lines"
                # 'partner_id': False,
                'date_order': date_order,
                'amount_paid':  amount_paid,
                'amount_total':  formatPrice(order['partner_order_total']),
                'amount_tax': 0,
                'amount_return': 0,
                'state': 'paid',
                'delivery_note': notes,
                'payment_ids': [(0,0,{
                    'amount': amount_paid,
                    'payment_date': date_order,
                    'payment_method_id': deliveroo_provider.payment_method_id.id,
                })],
                'last_order_preparation_change': '{}',
            })
            pos_config_sudo._send_delivery_order_count(delivery_order.id)
        else:
            #See what we should do if the order already exists (like an update or something)
            pass

        # request.env['pos.delivery.service'].sudo().search([('service', '=', 'deliveroo')])._new_order(order_id_sudo)
        # find a way do get the proper domain for the delivery service
        # print(request.env['pos.delivery.service'].sudo().search([('service', '=', 'deliveroo')])._refresh_access_token())
        # if data['event'] == 'order.new':
            # ask the preparation display for acceptation or the pos screen
            # accept = True #accept = true for the deliveroo tests
            # if accept:
            #     request.env['pos.delivery.service'].sudo().search([])[0].sudo()._accept_order(data['body']['order']['id'])
            # else:
            #     request.env['pos.delivery.service'].sudo().search([])[0].sudo()._reject_order(data['body']['order']['id'], "busy")
        if data['event'] == 'order.status_update':
            # TODO: in the 'order.status_update' event, deliveroo tells us if they have accepted the order or not
            # we should only start preparing the order if it has been accepted by deliveroo
            if data['body']['order']['status'] == 'accepted':
                pass
                #should move the order to preparing state.
                # request.env['pos.delivery.service'].sudo().search([])[0].sudo()._confirm_accepted_order(data['body']['order']['id']) -> this should be called when the order goes to the cooking stage.
            elif data['body']['order']['status'] == 'cancelled':
                #should cancel the order here
                pass
        return
