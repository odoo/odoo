from odoo import http
from odoo.http import request
import requests
import json
import logging
_logger = logging.getLogger(__name__)


class SystemParameterController(http.Controller):

    @http.route('/custom_module/ticketNumber', type='json', auth='public', methods=['POST'])
    def get_ticket_number_by_order_id(self):
        data = json.loads(request.httprequest.data)
        pos_order_model = request.env['pos.order'].sudo()

        if not data['order_id']:
            count = pos_order_model.get_today_ticket_number()
            return {'ticket_number': count}

        order = pos_order_model.search([('id', '=', data['order_id'])], limit=1)

        if not order:
            return {'error': f"Order with ID {data['order_id']} not found."}
        print("'ticket_number': ",order.ticket_number)
        return {'ticket_number': order.ticket_number}

    @http.route('/custom_module/restaurant_id', type='json', auth='public', methods=['POST'])
    def get_restaurant_id(self):
        restaurant_id = request.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        return {'restaurant_id': restaurant_id}

    @http.route('/custom_module/local_ip', type='json', auth='public', methods=['POST'])
    def get_local_ip(self):
        local_ip = request.env['ir.config_parameter'].sudo().get_param('local_ip')
        if not local_ip:
            return {'error': 'Local IP not configured'}

        print_receipt_url = f"{local_ip}/print_receipt"
        print("url", print_receipt_url)

        data = json.loads(request.httprequest.data.decode('utf-8'))
        print("data passed", data)

        headers = {'Content-Type': 'application/json'}

        response = requests.post(print_receipt_url, headers=headers, json=data)
        print("response content", response.content)

        if response.status_code == 200:
            print("Response from the controller", response)
            return True
        else:
            return {'error': f"Failed to print: {response.status_code} - {response.text}"}

    @http.route('/custom_module/public_ip', type='json', auth='public', methods=['POST'])
    def get_public_ip(self):
        print_port = request.env['ir.config_parameter'].sudo().get_param('print_port')
        if not print_port:
            return {'error': 'Public IP "print_port" not configured'}

        data = json.loads(request.httprequest.data.decode('utf-8'))
        _logger.info("data => : %s", data)
        print("data passed", data)

        print_receipt_url = f"http://{data['public_ip']}:{print_port}/print_receipt"
        _logger.info("print_receipt_url: %s", print_receipt_url)
        print("url", print_receipt_url)

        headers = {'Content-Type': 'application/json'}

        response = requests.post(print_receipt_url, headers=headers, json=data)
        print("response content", response.content)

        if response.status_code == 200:
            print("Response from the controller", response)
            return True
        else:
            return {'error': f"Failed to print: {response.status_code} - {response.text}"}

