import json
import logging
from odoo import http, fields
from odoo.http import request
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
import uuid
from datetime import date, datetime

_logger = logging.getLogger(__name__)


def json_default(obj):
    """Fonction de sérialisation personnalisée pour les objets non standards"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    raise TypeError(f"Type {type(obj)} not serializable")


class OrderController(PosSelfOrderController):

    @http.route('/new_order', type='http', auth='public', methods=['POST'], csrf=False)
    def process_mobile_order(self, **kwargs):
        _logger.info('******************* process_mobile_order **************')
        try:
            raw_data = request.httprequest.data
            data = json.loads(raw_data.decode('utf-8')) if raw_data else {}
            order_data = data.get('order', {})

            if not order_data or 'lines' not in order_data:
                return http.Response(json.dumps({"error": "Invalid order data"}),
                                     content_type='application/json', status=400)

            pos_config_id = data.get('pos_config_id')
            table_identifier = data.get('table_identifier')
            access_token = data.get('access_token')
            device_type = data.get('device_type', 'mobile')

            if not all([pos_config_id, table_identifier, access_token]):
                return http.Response(json.dumps({"error": "Missing required parameters"}),
                                     content_type='application/json', status=400)

            pos_config = request.env['pos.config'].sudo().browse(pos_config_id)
            if not pos_config or not pos_config.current_session_id:
                return http.Response(json.dumps({"error": "POS configuration or session not found"}),
                                     content_type='application/json', status=400)

            restaurant_table = request.env['restaurant.table'].sudo().search([
                ('identifier', '=', table_identifier),
            ], limit=1)

            if not restaurant_table:
                return http.Response(json.dumps({"error": f"Table '{table_identifier}' not found"}),
                                     content_type='application/json', status=404)

            # Préparer les lignes de commande
            line_tuples = []
            for line in order_data['lines']:
                product = request.env['product.product'].sudo().search([
                    ('menupro_id', '=', line.get('menupro_id'))
                ], limit=1)

                if not product:
                    continue

                taxes_res = product.taxes_id.compute_all(
                    product.lst_price,
                    currency=pos_config.pricelist_id.currency_id,
                    quantity=line.get('qty', 1),
                    product=product
                )

                line_data = {
                    'product_id': product.id,
                    'qty': line.get('qty', 1),
                    'note': line.get('note', ''),
                    'price_unit': product.lst_price,
                    'price_subtotal': taxes_res['total_excluded'],
                    'price_subtotal_incl': taxes_res['total_included'],
                    'tax_ids': [(6, 0, product.taxes_id.ids)],
                    'uuid': str(uuid.uuid4()),
                }
                line_tuples.append((0, 0, line_data))

            # Gestion des commandes existantes
            existing_order = request.env['pos.order'].sudo().search([
                ('table_id', '=', restaurant_table.id),
                ('session_id', '=', pos_config.current_session_id.id),
                ('state', '=', 'draft')
            ], limit=1)

            if existing_order:
                # Ajouter les nouvelles lignes à la commande existante
                existing_order.write({'lines': line_tuples})
                existing_order._onchange_amount_all()

                # Solution alternative: synchroniser via la méthode standard
                # Préparer les données dans le format attendu par sync_from_ui
                order_data_for_sync = {
                    'id': existing_order.id,
                    'name': existing_order.name,
                    'pos_reference': existing_order.pos_reference,
                    'session_id': existing_order.session_id.id,
                    'date_order': fields.Datetime.to_string(existing_order.date_order),
                    'access_token': access_token,
                    'amount_total': existing_order.amount_total,
                    'amount_tax': existing_order.amount_tax,
                    'amount_paid': existing_order.amount_paid,
                    'amount_return': existing_order.amount_return,
                    'uuid': existing_order.uuid,
                    'table_id': restaurant_table.id,
                    'state': 'draft',
                    'takeaway': existing_order.takeaway,
                    'sequence_number': existing_order.sequence_number,
                    # Format spécial pour les lignes
                    'lines': [[0, 0, {
                        'product_id': line.product_id.id,
                        'qty': line.qty,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'price_subtotal_incl': line.price_subtotal_incl,
                        'tax_ids': line.tax_ids.ids,
                        'note': line.note,
                        'uuid': line.uuid,
                    }] for line in existing_order.lines]
                }

                # Synchroniser avec le POS
                result = request.env['pos.order'].sudo().sync_from_ui([order_data_for_sync])

                return http.Response(
                    json.dumps({
                        "success": True,
                        "order_id": existing_order.id,
                        "message": "Order lines added successfully"
                    }),
                    content_type='application/json',
                    status=200
                )

            else:
                sequence = request.env['ir.sequence'].sudo().next_by_code('pos.order')
                order_dict = {
                    'name': sequence,
                    'pos_reference': sequence,
                    'session_id': pos_config.current_session_id.id,
                    'date_order': fields.Datetime.now().isoformat(),
                    'lines': line_tuples,
                    'access_token': access_token,
                    'amount_total': sum(line[2]['price_subtotal_incl'] for line in line_tuples),
                    'amount_tax': sum(
                        line[2]['price_subtotal_incl'] - line[2]['price_subtotal'] for line in line_tuples),
                    'amount_paid': 0.0,
                    'amount_return': 0.0,
                    'uuid': str(uuid.uuid4()),
                    'table_id': restaurant_table.id,
                    'state': 'draft',
                    'takeaway': False,
                    'sequence_number': None,
                }

                # Appeler la méthode parente et convertir le résultat en réponse HTTP
                result = super().process_order_args(order_dict, access_token, table_identifier, device_type)

                # Sérialiser avec gestion des types spéciaux
                json_response = json.dumps(result, default=json_default)
                return http.Response(json_response, content_type='application/json', status=200)

        except Exception as e:
            _logger.exception("Error processing mobile order: %s", str(e))
            return http.Response(json.dumps({"error": str(e)}),
                                 content_type='application/json', status=500)