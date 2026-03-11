import math

from odoo import http
from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import AutoCompleteController
from odoo.fields import Domain
from odoo.http import request
from odoo.service.model import call_kw
from werkzeug.exceptions import Forbidden, NotFound, BadRequest, Unauthorized
from odoo.exceptions import MissingError
from odoo.tools import consteq


def _haversine_distance(lat1, long1, lat2, long2):
    """Compute the straight-line distance in km between two lat/long points."""
    R = 6371  # earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlong = math.radians(long2 - long1)
    arcsin = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlong / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(arcsin), math.sqrt(1 - arcsin))


class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-order/<device_type>/", auth="public", type="jsonrpc", website=True)
    def process_order(self, order, access_token, table_identifier, device_type):
        pos_config, table = self._verify_authorization(access_token, table_identifier, order)
        if not pos_config.self_ordering_mode == device_type:
            raise Unauthorized("Invalid device type")

        # Create a safe copy of the order with only the necessary fields for order creation to
        # avoid potential security issues and to reduce the payload size
        safe_data = pos_config.env['pos.order']._check_pos_order(pos_config, order, device_type, table)
        results = pos_config.env['pos.order'].sudo().with_company(pos_config.company_id.id).sync_from_ui([safe_data])
        order_ids = pos_config.env['pos.order'].browse([order['id'] for order in results['pos.order']])
        preset_id = order_ids.preset_id

        if preset_id and preset_id.service_at == 'delivery':
            self._ensure_delivery_fee(order_ids, preset_id)

        # Recompute all prices from newly created lines to ensure price correctness and
        # avoid potential manipulation from the frontend
        order_ids.recompute_prices()

        amount_total = order_ids.amount_total

        if amount_total == 0:
            order_ids.state = 'paid'
            order_ids._process_saved_order(False)
            order_ids._send_self_order_receipt()

        return self._generate_return_values(order_ids, pos_config)

    def _generate_return_values(self, order, config):
        orders = self.env['pos.order']._load_pos_self_data_read(order, config)

        for o in orders:
            del o['email']
            del o['mobile']

        return {
            'pos.order': self.env['pos.order']._load_pos_self_data_read(order, config),
            'pos.order.line': self.env['pos.order.line']._load_pos_self_data_read(order.lines, config),
            'pos.payment': self.env['pos.payment']._load_pos_self_data_read(order.payment_ids, config),
            'product.attribute.custom.value': self.env['product.attribute.custom.value']._load_pos_self_data_read(order.lines.custom_attribute_value_ids, config),
        }

    def _verify_line_price(self, lines, pos_config, preset_id):
        lines.order_id.recompute_prices()

    def _ensure_delivery_fee(self, order, preset):
        """Add or remove the delivery fee line based on the order total and preset configuration."""
        delivery_product = preset.delivery_product_id
        if not delivery_product:
            return

        non_delivery_lines = order.lines.filtered(
            lambda l: l.product_id != delivery_product
        )
        tax_included = order.config_id.iface_tax_included == 'total'
        total_field = 'price_subtotal_incl' if tax_included else 'price_subtotal'
        non_delivery_total = sum(non_delivery_lines.mapped(total_field))

        free_min = preset.free_delivery_min_amount
        delivery_is_free = bool(free_min) and non_delivery_total >= free_min

        existing_delivery_lines = order.lines.filtered(
            lambda l: l.product_id == delivery_product
        )
        if delivery_is_free:
            existing_delivery_lines.unlink()
        elif not existing_delivery_lines:
            new_line = order.env['pos.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': delivery_product.id,
                'qty': 1,
                'price_subtotal': 0.0,
                'price_subtotal_incl': 0.0,
                'full_product_name': delivery_product.name,
            })
            order._compute_line_price(new_line, price=preset.delivery_product_price)

    @http.route('/pos-self-order/validate-partner', auth='public', type='jsonrpc', website=True)
    def validate_partner(self, access_token, name, phone, street, zip, city, country_id, state_id=None, partner_id=None, email=None, preset_id=None):
        pos_config = self._verify_pos_config(access_token)
        preset = pos_config.env['pos.preset'].browse(int(preset_id)) if preset_id else False
        existing_partner = pos_config.env['res.partner'].sudo().browse(int(partner_id)) if partner_id else False

        if existing_partner and existing_partner.exists():
            if preset and preset.exists() and preset.service_at == 'delivery':
                error = self._check_delivery_address_for_partner(preset, existing_partner)
                if error:
                    return {'error': error}
            return {
                'res.partner': existing_partner.read(['id'], load=False),
            }

        state_id = pos_config.env['res.country.state'].browse(int(state_id)) if state_id else False
        country_id = pos_config.env['res.country'].browse(int(country_id))
        partner_sudo = request.env['res.partner'].sudo().create({
            'name': name,
            'email': email,
            'phone': phone,
            'street': street,
            'zip': zip,
            'city': city,
            'country_id': country_id.id,
            'state_id': state_id.id if state_id else False,
            'company_id': pos_config.company_id.id,
        })
        if preset and preset.exists() and preset.service_at == 'delivery':
            error = self._check_delivery_address_for_partner(preset, partner_sudo)
            if error:
                return {'error': error}

        return {
            'res.partner': partner_sudo.read(['id'], load=False),
        }

    def _check_delivery_address_for_partner(self, preset, partner):
        if not partner.partner_latitude and not partner.partner_longitude:
            partner.geo_localize()
        if not partner.partner_latitude and not partner.partner_longitude:
            return {
                'type': 'address',
                'message': self.env._("We couldn't locate this address. Please enter a complete address with a street number."),
            }
        if not preset.delivery_from_address:
            return None
        distance_km = _haversine_distance(
            partner.partner_latitude, partner.partner_longitude,
            preset.delivery_from_latitude, preset.delivery_from_longitude,
        )
        max_distance = preset.delivery_max_distance_km
        max_distance_km = max_distance * 1.60934 if preset.delivery_distance_unit == 'mi' else max_distance
        if max_distance_km and distance_km > max_distance_km:
            return {
                'type': 'delivery',
                'message': self.env._("Delivery isn't available for this address. You can still place your order using another method."),
            }
        return None

    @http.route('/pos-self-order/remove-order', auth='public', type='jsonrpc', website=True)
    def remove_order(self, access_token, order_id, order_access_token):
        pos_config = self._verify_pos_config(access_token)
        pos_order = pos_config.env['pos.order'].browse(order_id)

        if not pos_order.exists() or not consteq(pos_order.access_token, order_access_token):
            raise MissingError(self.env._("Your order does not exist or has been removed"))

        if pos_order.state != 'draft':
            raise Unauthorized(self.env._("You are not authorized to remove this order"))

        pos_order.remove_from_ui([pos_order.id])

    @http.route('/pos-self-order/get-user-data', auth='public', type='jsonrpc', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens, table_identifier=None):
        pos_config = self._verify_pos_config(access_token)
        table = pos_config.env["restaurant.table"].search([('identifier', '=', table_identifier)], limit=1)
        domain = False

        if not table_identifier or pos_config.self_ordering_pay_after == 'each':
            domain = [(False, '=', True)]
        else:
            domain = ['&', '&',
                ('table_id', '=', table.id),
                ('state', '=', 'draft'),
                ('access_token', 'not in', [data.get('access_token') for data in order_access_tokens])
            ]

        for data in order_access_tokens:
            domain = Domain.OR([domain, ['&',
                ('access_token', '=', data['access_token']),
                '|',
                ('write_date', '>', data.get('write_date')),
                ('state', '!=', data.get('state')),
            ]])
        orders = pos_config.env['pos.order'].search(domain)
        access_tokens = set({o.get('access_token') for o in order_access_tokens})
        # Do not use session.order_ids, it may fail if there is shared sessions
        existing_order_tokens = pos_config.env['pos.order'].search([('access_token', 'in', access_tokens)]).mapped('access_token')
        if deleted_order_tokens := list(access_tokens - set(existing_order_tokens)):
            # Remove orders that no longer exist on the server but are still shown in the self-order UI
            pos_config._notify('REMOVE_ORDERS', {'deleted_order_tokens': deleted_order_tokens})
        return self._generate_return_values(orders, pos_config) if orders else {}

    @http.route('/kiosk/payment/<int:pos_config_id>/<device_type>', auth='public', type='jsonrpc', website=True)
    def pos_self_order_kiosk_payment(self, pos_config_id, order, payment_method_id, access_token, device_type):
        pos_config = self._verify_pos_config(access_token)
        results = self.process_order(order, access_token, None, device_type)

        if not results['pos.order'][0].get('id'):
            raise BadRequest("Something went wrong")

        # access_token verified in process_new_order
        order_sudo = pos_config.env['pos.order'].browse(results['pos.order'][0]['id'])
        payment_method_sudo = pos_config.env["pos.payment.method"].browse(payment_method_id)
        if not order_sudo or not payment_method_sudo or payment_method_sudo not in order_sudo.config_id.payment_method_ids:
            raise NotFound("Order or payment method not found")

        status = payment_method_sudo._payment_request_from_kiosk(order_sudo)

        if not status:
            raise BadRequest("Something went wrong")

        return {'order': self.env['pos.order']._load_pos_self_data_read(order_sudo, pos_config), 'payment_status': status}

    @http.route("/kiosk/payment_method_action/<action>", auth="public", type="jsonrpc", website=True)
    def pos_self_order_kiosk_payment_method_action(self, access_token, action, args, kwargs):
        pos_config = self._verify_pos_config(access_token)
        payment_method_env = pos_config.env["pos.payment.method"]
        if pos_config.self_ordering_mode != "kiosk":
            raise Forbidden("Method only allowed in kiosk mode")
        if args and isinstance(args[0], list):
            if len(args[0]) != 1:
                raise BadRequest("Only one payment method ID should be provided")
            if not payment_method_env.search_count([("id", "=", args[0]), ("config_ids", "in", pos_config.id)]):
                raise NotFound("Payment method not found in config")
        if action not in payment_method_env._allowed_actions_in_self_order():
            raise Forbidden(f"Method '{action}' is forbidden in the self order kiosk")

        return call_kw(payment_method_env, action, args, kwargs)

    @http.route('/pos_self_order/kiosk/increment_nb_print/', auth='public', type='jsonrpc', website=True)
    def pos_kiosk_increment_nb_print(self, access_token, order_id, order_access_token):
        pos_config = self._verify_pos_config(access_token)
        pos_order = pos_config.env['pos.order'].browse(order_id)

        if not pos_order.exists() or not consteq(pos_order.access_token, order_access_token):
            raise MissingError(self.env._("Your order does not exist or has been removed"))

        pos_order.write({
            'nb_print': 1,
        })

    @http.route('/pos-self-order/change-printer-status', auth='public', type='jsonrpc', website=True)
    def change_printer_status(self, access_token, has_paper):
        pos_config = self._verify_pos_config(access_token)
        if has_paper != pos_config.has_paper:
            pos_config.write({'has_paper': has_paper})

    @http.route('/pos-self-order/get-slots', auth='public', type='jsonrpc', website=True)
    def get_slots(self, access_token, preset_id):
        pos_config = self._verify_pos_config(access_token)
        preset = pos_config.env['pos.preset'].browse(preset_id)
        return preset.get_available_slots()

    def _get_order_prices(self, lines):
        amount_untaxed = sum(lines.mapped('price_subtotal'))
        amount_total = sum(lines.mapped('price_subtotal_incl'))
        return amount_total, amount_untaxed

    @http.route('/pos-self/autocomplete/address', methods=['POST'], type='jsonrpc', auth='public', website=True)
    def pos_self_order_autocomplete_address(self, access_token, partial_address, **kwargs):
        self._verify_pos_config(access_token)
        api_key = request.env['ir.config_parameter'].sudo().get_str('google_address_autocomplete.google_places_api_key') or None
        if not api_key:
            return {'results': []}
        return AutoCompleteController()._perform_place_search(partial_address, api_key=api_key)

    @http.route('/pos-self/autocomplete/address_full', methods=['POST'], type='jsonrpc', auth='public', website=True)
    def pos_self_order_autocomplete_address_full(self, access_token, address, google_place_id=None, **kwargs):
        self._verify_pos_config(access_token)
        api_key = request.env['ir.config_parameter'].sudo().get_str('google_address_autocomplete.google_places_api_key') or None
        if not api_key:
            return {'address': None}
        return AutoCompleteController()._perform_complete_place_search(address, api_key=api_key, google_place_id=google_place_id)

    def _verify_pos_config(self, access_token, check_active_session=True):
        """
        Finds the pos.config with the given access_token and returns a record with reduced privileges.
        The record is has no sudo access and is in the context of the record's company and current pos.session's user.
        """
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)
        if self._verify_config_constraint(pos_config_sudo, check_active_session):
            raise Unauthorized("Invalid access token")
        company = pos_config_sudo.company_id
        user = pos_config_sudo.self_ordering_default_user_id
        return pos_config_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)

    def _verify_config_constraint(self, pos_config_sudo, check_active_session=True):
        return not pos_config_sudo or (pos_config_sudo.self_ordering_mode != 'mobile' and pos_config_sudo.self_ordering_mode != 'kiosk') or (check_active_session and not pos_config_sudo.has_active_session)

    def _verify_authorization(self, access_token, table_identifier, order):
        """
        Similar to _verify_pos_config but also looks for the restaurant.table of the given identifier.
        The restaurant.table record is also returned with reduced privileges.
        """
        pos_config = self._verify_pos_config(access_token)
        table_sudo = request.env["restaurant.table"].sudo().search([('identifier', '=', table_identifier)], limit=1)
        preset = request.env['pos.preset'].sudo().browse(order.get('preset_id'))
        is_takeaway = order and pos_config.use_presets and preset and preset.service_at != 'table'
        if not table_sudo and not pos_config.self_ordering_mode == 'kiosk' and pos_config.self_ordering_service_mode == 'table' and not is_takeaway:
            raise Unauthorized("Table not found")

        company = pos_config.company_id
        user = pos_config.self_ordering_default_user_id
        table = table_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)
        return pos_config, table

    @http.route(['/pos-self/ping'], type='jsonrpc', auth='public')
    def pos_ping(self, access_token):
        self._verify_pos_config(access_token, check_active_session=False)
        return {'response': 'pong'}
