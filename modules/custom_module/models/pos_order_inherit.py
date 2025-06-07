from odoo import models, fields, api, tools
import requests
import logging
import json
from datetime import datetime


_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    menupro_id = fields.Char(string='MenuPro ID')
    origine = fields.Char(string='Origine')
    ticket_number = fields.Integer(string='Ticket Number', help='Ticket number for the order')


    @api.model
    def sync_from_ui(self, orders):
        result = super().sync_from_ui(orders)
        created_orders = result.get('pos.order', {})
        for order in created_orders:
            self._sync_to_menupro(order)
            # Generate a ticket_number
            if 'ticket_number' not in order:
                order['ticket_number'] = self.get_today_ticket_number()
        return result

    @api.model
    def _sync_to_menupro(self, order):
        restaurant_id = self.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        odoo_secret_key = tools.config.get("odoo_secret_key")
        api_url = "https://api.finance.visto.group/orders/order/upsert"

        if not restaurant_id or not odoo_secret_key:
            _logger.error("Secret key or restaurant ID not configured. Skipped sync to menupro")
            return

        headers = {'x-odoo-key': odoo_secret_key}
        payload = self._prepare_api_payload(order, restaurant_id)
        # print("Payload to be sent to our server =>", payload)

        try:
            response = requests.patch(api_url, json=payload, headers=headers)
            # print('response of finance =>', response.text)
        except Exception as e:
            _logger.error("Error API: %s", str(e))
            raise

        if response.status_code == 200:
            response_data = response.json().get("data")
            menupro_id = response_data.get('menuproId')
            if menupro_id:
                self._update_menupro_id(menupro_id, order.get('id'))
        else:
            _logger.error(f"Failed to sync to Menupro order with ID")

    @api.model
    def _update_menupro_id(self, menupro_id, order_id):
        pos_order = self.env['pos.order'].sudo().search([('id', '=', order_id)], limit=1)
        if pos_order:
            pos_order.write({'menupro_id': menupro_id})
            print(f"Order {pos_order.name} updated with menupro_id {menupro_id}")
        else:
            _logger.warning(f"No POS order found with ID {order_id}")

    @api.model
    def _prepare_api_payload(self, order_data, restaurant_id):
        try:
            # Formulate date_order to ISO format
            date_order = order_data.get('date_order')
            if isinstance(date_order, datetime):
                date_order = date_order.isoformat()

            payload = {
                "restaurantId": restaurant_id,
                "order": {
                    "id": order_data.get('id'),
                    "name": order_data.get('pos_reference', ''),
                    "amount_paid": order_data.get('amount_paid', 0),
                    "amount_total": order_data.get('amount_total', 0),
                    "amount_tax": order_data.get('amount_tax', 0),
                    "amount_return": order_data.get('amount_return', 0),
                    "lines": [],
                    "statement_ids": [],
                    "pos_session_id": order_data.get('session_id'),
                    "pricelist_id": order_data.get('pricelist_id', False),
                    "partner_id": order_data.get('partner_id', False),
                    "user_id": order_data.get('user_id'),
                    "uid": order_data.get('uuid', ''),
                    "sequence_number": order_data.get('sequence_number', 0),
                    "date_order": date_order,
                    "fiscal_position_id": order_data.get('fiscal_position_id', False),
                    "server_id": False,
                    "to_invoice": order_data.get('to_invoice', False),
                    "is_tipped": order_data.get('is_tipped', False),
                    "tip_amount": order_data.get('tip_amount', 0),
                    "access_token": order_data.get('access_token', ''),
                    "last_order_preparation_change": order_data.get('last_order_preparation_change', ''),
                    "ticket_code": order_data.get('ticket_code', ''),
                    "table_id": order_data.get('table_id'),
                    "customer_count": order_data.get('customer_count', 1),
                    "booked": True,
                    "employee_id": order_data.get('employee_id'),
                    "menupro_id": order_data.get('menupro_id', False),
                    "status": "validate",
                    "menupro_fee": 0.5,
                    "ticketNumber": int(order_data.get('pos_reference', '0-0-0').split('-')[-1]),
                    "state": order_data.get('state', 'draft')
                }
            }

            # Get kitchen-ordered lines
            kitchen_lines = {}
            if order_data.get('last_order_preparation_change'):
                try:
                    prep_data = json.loads(order_data['last_order_preparation_change'])
                    kitchen_lines = prep_data.get('lines', {})
                except json.JSONDecodeError:
                    pass

            # Process all order lines
            for line_id in order_data['lines']:
                line = self.env['pos.order.line'].sudo().search([('id', '=', line_id)], limit=1)
                if not line:
                    continue

                line_data = {
                    "id": line.id,
                    "name": line.name,
                    "full_product_name": line.full_product_name or line.product_id.display_name,
                    "uuid": line.uuid,
                    "note": line.note or "",
                    "customer_note": line.customer_note or "",
                    "notice": line.notice or "",
                    "product_id": line.product_id.id,  # Use ID instead of model instance
                    "order_id": line.order_id.id,  # Use ID instead of model instance
                    "combo_parent_id": line.combo_parent_id.id if line.combo_parent_id else False,
                    "combo_item_id": line.combo_item_id.id if line.combo_item_id else False,
                    "price_type": line.price_type,
                    "price_unit": line.price_unit,
                    "qty": line.qty,
                    "price_subtotal": line.price_subtotal,
                    "price_subtotal_incl": line.price_subtotal_incl,
                    "discount": line.discount,
                    "skip_change": False,
                    "is_total_cost_computed": line.is_total_cost_computed,
                    "is_edited": line.is_edited,
                    "price_extra": line.price_extra,
                    "is_sent_to_kitchen": line.uuid in kitchen_lines,
                }
                payload['order']['lines'].append(line_data)

            return payload
        except Exception as e:
            _logger.error("Error preparing API payload: %s", str(e))
            raise


    def get_today_ticket_number(self):
        """Get the count of orders made today (ignoring time)"""
        today = fields.Date.today()
        # Search for orders where the date part of date_order matches today
        orders_today = self.search_count([
            ('date_order', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
            ('date_order', '<=', fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))),
        ])
        return orders_today + 1

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['ticket_number'] = self.get_today_ticket_number()
        return super().create(vals_list)