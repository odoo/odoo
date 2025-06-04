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

            # Gestion des commandes existantes
            existing_order = request.env['pos.order'].sudo().search([
                ('table_id', '=', restaurant_table.id),
                ('session_id', '=', pos_config.current_session_id.id),
                ('state', '=', 'draft')
            ], limit=1)

            # Préparer les lignes de commande
            line_operations = []
            line_dicts = []  # Pour la synchronisation

            for line in order_data['lines']:
                product = request.env['product.product'].sudo().search([
                    ('menupro_id', '=', line.get('menupro_id'))
                ], limit=1)

                if not product:
                    continue

                qty = line.get('qty', 1)
                note = line.get('note', '')
                menupro_id = line.get('menupro_id')

                # Calcul des taxes
                taxes_res = product.taxes_id.compute_all(
                    product.lst_price,
                    currency=pos_config.pricelist_id.currency_id,
                    quantity=qty,
                    product=product
                )

                line_uuid = str(uuid.uuid4())

                # Format pour synchronisation
                line_dict = {
                    'product_id': product.id,
                    'qty': qty,
                    'price_unit': product.lst_price,
                    'price_subtotal': taxes_res['total_excluded'],
                    'price_subtotal_incl': taxes_res['total_included'],
                    'tax_ids': product.taxes_id.ids,
                    'note': note,
                    'uuid': line_uuid,
                }

                # Si commande existante, vérifier si le produit est déjà présent
                if existing_order:
                    # Chercher une ligne existante avec le même produit et même note
                    existing_line = None
                    for ol in existing_order.lines:
                        if ol.product_id.id == product.id and ol.note == note:
                            existing_line = ol
                            break

                    if existing_line:
                        # Mise à jour de la quantité
                        new_qty = existing_line.qty + qty
                        line_dict['id'] = existing_line.id
                        line_dict['qty'] = new_qty
                        line_dict['price_subtotal'] = existing_line.price_unit * new_qty
                        line_dict['price_subtotal_incl'] = existing_line.price_unit * new_qty * (
                                    1 + existing_line.tax_ids.amount / 100)

                        # Ajouter l'opération de mise à jour
                        line_operations.append((1, existing_line.id, {
                            'qty': new_qty,
                            'price_subtotal': line_dict['price_subtotal'],
                            'price_subtotal_incl': line_dict['price_subtotal_incl'],
                        }))
                    else:
                        # Nouvelle ligne
                        line_dict['id'] = False
                        line_operations.append((0, 0, {
                            'product_id': product.id,
                            'qty': qty,
                            'note': note,
                            'price_unit': product.lst_price,
                            'price_subtotal': taxes_res['total_excluded'],
                            'price_subtotal_incl': taxes_res['total_included'],
                            'tax_ids': [(6, 0, product.taxes_id.ids)],
                            'uuid': line_uuid,
                        }))
                else:
                    # Nouvelle commande
                    line_operations.append((0, 0, {
                        'product_id': product.id,
                        'qty': qty,
                        'note': note,
                        'price_unit': product.lst_price,
                        'price_subtotal': taxes_res['total_excluded'],
                        'price_subtotal_incl': taxes_res['total_included'],
                        'tax_ids': [(6, 0, product.taxes_id.ids)],
                        'uuid': line_uuid,
                    }))

                line_dicts.append(line_dict)

            if existing_order:
                # Appliquer les opérations sur les lignes sans effacer les existantes
                # Nous allons traiter les mises à jour et les ajouts séparément

                # 1. Mettre à jour les lignes existantes
                for op in line_operations:
                    if op[0] == 1:  # Mise à jour
                        request.env['pos.order.line'].sudo().browse(op[1]).write(op[2])

                # 2. Ajouter les nouvelles lignes
                new_lines = [op for op in line_operations if op[0] == 0]
                if new_lines:
                    existing_order.write({'lines': new_lines})

                # Recalculer les totaux
                existing_order._onchange_amount_all()

                # Préparer les données pour la synchronisation
                # Nous devons inclure TOUTES les lignes de la commande
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
                    # Format spécial pour les lignes - toutes les lignes existantes
                    'lines': [[
                        1 if line.id else 0,
                        line.id if line.id else 0,
                        {
                            'product_id': line.product_id.id,
                            'qty': line.qty,
                            'price_unit': line.price_unit,
                            'price_subtotal': line.price_subtotal,
                            'price_subtotal_incl': line.price_subtotal_incl,
                            'tax_ids': line.tax_ids.ids,
                            'note': line.note or '',
                            'uuid': line.uuid,
                        }
                    ] for line in existing_order.lines]
                }

                # Synchroniser avec le POS
                result = request.env['pos.order'].sudo().sync_from_ui([order_data_for_sync])

                return http.Response(
                    json.dumps({
                        "success": True,
                        "order_id": existing_order.id,
                        "message": "Order updated successfully"
                    }),
                    content_type='application/json',
                    status=200
                )

            else:
                # Créer une nouvelle commande
                sequence = request.env['ir.sequence'].sudo().next_by_code('pos.order')
                order_dict = {
                    'name': sequence,
                    'pos_reference': sequence,
                    'session_id': pos_config.current_session_id.id,
                    'date_order': fields.Datetime.now().isoformat(),
                    'lines': line_operations,
                    'access_token': access_token,
                    'amount_total': sum(line[2]['price_subtotal_incl'] for line in line_operations),
                    'amount_tax': sum(
                        line[2]['price_subtotal_incl'] - line[2]['price_subtotal'] for line in line_operations),
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