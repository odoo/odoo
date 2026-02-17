from odoo import http, fields
from odoo.fields import Domain
from odoo.http import request
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized
from odoo.exceptions import MissingError
from odoo.tools import consteq


class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-order/<device_type>/", auth="public", type="jsonrpc", website=True)
    def process_order(self, order, access_token, table_identifier, device_type):
        pos_config, table = self._verify_authorization(access_token, table_identifier, order)
        preset_id = order['preset_id'] if pos_config.use_presets else False
        preset_id = pos_config.env['pos.preset'].browse(preset_id) if preset_id else False

        if not preset_id and pos_config.use_presets:
            raise BadRequest("Invalid preset")

        # Create the order
        if 'picking_type_id' in order:
            del order['picking_type_id']

        if 'name' in order:
            del order['name']

        pos_reference, tracking_number = pos_config._get_next_order_refs()
        if device_type == 'kiosk':
            order['floating_order_name'] = f"Table tracker {order['table_stand_number']}" if order.get('table_stand_number') else tracking_number

        if not order.get('floating_order_name') and table:
            floating_order_name = f"Self-Order T {table.table_number}"
        elif not order.get('floating_order_name'):
            floating_order_name = f"Self-Order {tracking_number}"

        # The goal of this is to reduce collisions with other pos.order tracking numbers
        # when several kiosks are used with different pos.configurations.
        # This is a little hack in stable, in master the prefix will be chosen differently.
        prefix = f"K{pos_config.id}-" if device_type == "kiosk" else "S"
        order['pos_reference'] = pos_reference
        order['source'] = 'kiosk' if device_type == 'kiosk' else 'mobile'
        order['floating_order_name'] = order.get('floating_order_name') or floating_order_name
        order['tracking_number'] = f"{prefix}{tracking_number}"
        order['user_id'] = request.session.uid
        order['date_order'] = str(fields.Datetime.now())
        order['fiscal_position_id'] = preset_id.fiscal_position_id.id if preset_id else pos_config.default_fiscal_position_id.id
        order['pricelist_id'] = preset_id.pricelist_id.id if preset_id else pos_config.pricelist_id.id
        order['self_ordering_table_id'] = table.id if table else False

        results = pos_config.env['pos.order'].sudo().with_company(pos_config.company_id.id).sync_from_ui([order])
        line_ids = pos_config.env['pos.order.line'].browse([line['id'] for line in results['pos.order.line']])
        order_ids = pos_config.env['pos.order'].browse([order['id'] for order in results['pos.order']])

        self._verify_line_price(line_ids, pos_config, preset_id)

        amount_total, amount_untaxed = self._get_order_prices(order_ids.lines)
        order_ids.write({
            'state': 'paid' if amount_total == 0 else 'draft',
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        if amount_total == 0:
            order_ids._process_saved_order(False)

        if preset_id and preset_id.mail_template_id:
            order_ids._send_self_order_receipt()

        return self._generate_return_values(order_ids, pos_config)

    def _generate_return_values(self, order, config):
        return {
            'pos.order': self.env['pos.order']._load_pos_self_data_read(order, config),
            'res.partner': self.env['res.partner']._load_pos_self_data_read(order.partner_id, config),
            'pos.order.line': self.env['pos.order.line']._load_pos_self_data_read(order.lines, config),
            'pos.payment': self.env['pos.payment']._load_pos_self_data_read(order.payment_ids, config),
            'product.attribute.custom.value': self.env['product.attribute.custom.value']._load_pos_self_data_read(order.lines.custom_attribute_value_ids, config),
        }

    def _verify_line_price(self, lines, pos_config, preset_id):
        pricelist = preset_id.pricelist_id or pos_config.pricelist_id if preset_id else pos_config.pricelist_id

        for line in lines:
            if len(line.combo_line_ids) == 0:
                continue

            product = line.product_id
            lst_price = pricelist._get_product_price(product, quantity=line.qty) if pricelist else product.lst_price
            selected_attributes = line.attribute_value_ids
            price_extra = sum(attr.price_extra for attr in selected_attributes if attr.attribute_id.create_variant != 'always')
            lst_price += price_extra
            fiscal_pos = preset_id.fiscal_position_id or pos_config.default_fiscal_position_id if preset_id else pos_config.default_fiscal_position_id
            self._compute_combo_price(line, pricelist, fiscal_pos)

    def _compute_combo_price(self, parent_line, pricelist, fiscal_position):
        """
        This method is a python version of odoo/addons/point_of_sale/static/src/app/models/utils/compute_combo_items.js
        It is used to compute the price of combo items on the server side when an order is received from
        the POS frontend. In an accounting perspective, isn't correct but we still waiting the combo
        computation from accounting side.
        """
        child_lines = parent_line.combo_line_ids
        currency = parent_line.order_id.currency_id
        taxes = fiscal_position.map_tax(parent_line.product_id.taxes_id)
        parent_line.tax_ids = taxes
        parent_lst_price = pricelist._get_product_price(parent_line.product_id, parent_line.qty)
        child_line_free = []
        child_line_extra = []

        child_lines_by_combo = {}
        for line in child_lines:
            combo = line.combo_item_id.combo_id
            child_lines_by_combo.setdefault(combo, []).append(line)

        for combo, child_lines in child_lines_by_combo.items():
            free_count = 0
            max_free = combo.qty_free

            for line in child_lines:
                qty_free = max(0, max_free - free_count)
                free_qty = min(line.qty, qty_free)
                extra_qty = line.qty - free_qty

                if free_qty > 0:
                    child_line_free.append(line)
                    free_count += free_qty

                if extra_qty > 0:
                    child_line_extra.append(line)

        original_total = sum(line.combo_item_id.combo_id.base_price * line.qty for line in child_line_free if line.combo_item_id.combo_id.qty_free > 0)
        remaining_total = parent_lst_price

        for index, child in enumerate(child_line_free):
            combo_item = child.combo_item_id
            combo = combo_item.combo_id
            unit_devision_factor = original_total or 1
            price_unit = currency.round(combo.base_price * parent_lst_price / unit_devision_factor)
            remaining_total -= price_unit * child.qty

            if index == len(child_line_free) - 1:
                price_unit += remaining_total

            selected_attributes = child.attribute_value_ids
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            total_price = price_unit + price_extra + child.combo_item_id.extra_price
            child.price_unit = total_price

        for child in child_line_extra:
            combo_item = child.combo_item_id
            price_unit = currency.round(combo_item.combo_id.base_price)
            selected_attributes = child.attribute_value_ids
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            total_price = price_unit + price_extra + child.combo_item_id.extra_price
            child.price_unit = total_price

    @http.route('/pos-self-order/validate-partner', auth='public', type='jsonrpc', website=True)
    def validate_partner(self, access_token, name, phone, street, zip, city, country_id, state_id=None, partner_id=None, email=None):
        pos_config = self._verify_pos_config(access_token)
        existing_partner = pos_config.env['res.partner'].sudo().browse(int(partner_id)) if partner_id else False

        if existing_partner and existing_partner.exists():
            return {
                'res.partner': self.env['res.partner']._load_pos_self_data_read(existing_partner, pos_config),
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

        return {
            'res.partner': self.env['res.partner']._load_pos_self_data_read(partner_sudo, pos_config),
        }

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
