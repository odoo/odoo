# -*- coding: utf-8 -*-
import re
from odoo import Command, http, _
from odoo.http import request
from odoo.osv import expression
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized
from odoo.exceptions import MissingError
from odoo.tools import consteq

class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-order/<device_type>/", auth="public", type="json", website=True)
    def process_order(self, order, access_token, table_identifier, device_type):
        return self.process_order_args(order, access_token, table_identifier, device_type, **{})

    @http.route("/pos-self-order/process-order-args/<device_type>/", auth="public", type="json", website=True)
    def process_order_args(self, order, access_token, table_identifier, device_type, **kwargs):
        is_takeaway = order.get('takeaway')
        pos_config, table = self._verify_authorization(access_token, table_identifier, is_takeaway)
        pos_session = pos_config.current_session_id

        ir_sequence_session = pos_config.env['ir.sequence'].with_context(company_id=pos_config.company_id.id).next_by_code(f'pos.order_{pos_session.id}')
        sequence_number = order.get('sequence_number')
        if not sequence_number:
            sequence_number = re.findall(r'\d+', ir_sequence_session)[0]
        order_reference = self._generate_unique_id(pos_session.id, pos_config.id, sequence_number, device_type)
        order['pos_reference'] = order_reference
        order['name'] = order_reference

        # Create a safe copy of the order with only the necessary fields for order creation to
        # avoid potential security issues and to reduce the payload size
        safe_data = pos_config.env['pos.order']._check_pos_order(pos_config, order, table)
        results = pos_config.env['pos.order'].sudo().with_company(pos_config.company_id.id).sync_from_ui([safe_data])
        order_ids = pos_config.env['pos.order'].browse([order['id'] for order in results['pos.order']])

        # Recompute all prices from newly created lines to ensure price correctness and
        # avoid potential manipulation from the frontend
        order_ids.recompute_prices()

        amount_total, amount_untaxed = self._get_order_prices(order_ids.lines)
        order_ids.write({
            'state': 'paid' if amount_total == 0 else 'draft',
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        if amount_total == 0:
            order_ids._process_saved_order(False)

        order_ids.send_table_count_notification(order_ids.mapped('table_id'))
        return self._generate_return_values(order_ids, pos_config)

    def _generate_return_values(self, order, config_id):
        return {
            'pos.order': order.read(order._load_pos_data_fields(config_id.id), load=False),
            'pos.order.line': order.lines.read(order._load_pos_data_fields(config_id.id), load=False),
            'pos.payment': order.payment_ids.read(order.payment_ids._load_pos_data_fields(order.config_id.id), load=False),
            'pos.payment.method': order.payment_ids.mapped('payment_method_id').read(order.env['pos.payment.method']._load_pos_data_fields(order.config_id.id), load=False),
            'product.attribute.custom.value':  order.lines.custom_attribute_value_ids.read(order.lines.custom_attribute_value_ids._load_pos_data_fields(config_id.id), load=False),
        }

    def _verify_line_price(self, lines, pos_config, takeaway=False):
        lines.order_id.recompute_prices()

    @http.route('/pos-self-order/remove-order', auth='public', type='json', website=True)
    def remove_order(self, access_token, order_id, order_access_token):
        pos_config = self._verify_pos_config(access_token)
        pos_order = pos_config.env['pos.order'].browse(order_id)

        if not pos_order.exists() or not consteq(pos_order.access_token, order_access_token):
            raise MissingError(_("Your order does not exist or has been removed"))

        if pos_order.state != 'draft':
            raise Unauthorized(_("You are not authorized to remove this order"))

        pos_order.remove_from_ui([pos_order.id])

    @http.route('/pos-self-order/get-orders', auth='public', type='json', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens, table_identifier=None):
        pos_config = self._verify_pos_config(access_token)
        session = pos_config.current_session_id
        table = pos_config.env["restaurant.table"].search([('identifier', '=', table_identifier)], limit=1)
        domain = False

        if not table_identifier:
            domain = [(False, '=', True)]
        else:
            domain = ['&', '&',
                ('table_id', '=', table.id),
                ('state', '=', 'draft'),
                ('access_token', 'not in', [data.get('access_token') for data in order_access_tokens])
            ]

        for data in order_access_tokens:
            domain = expression.OR([domain, ['&',
                ('access_token', '=', data.get('access_token')),
                ('write_date', '>', data.get('write_date'))
            ]])

        orders = session.order_ids.filtered_domain(domain)
        if not orders:
            return {}

        return self._generate_return_values(orders, pos_config)

    @http.route('/pos-self-order/get-available-tables', auth='public', type='json', website=True)
    def get_available_tables(self, access_token, order_access_tokens):
        pos_config = self._verify_pos_config(access_token)
        orders = pos_config.current_session_id.order_ids.filtered_domain([
            ("access_token", "not in", order_access_tokens)
        ])
        available_table_ids = pos_config.floor_ids.table_ids - orders.mapped('table_id')
        return available_table_ids.read(['id'])

    @http.route('/kiosk/payment/<int:pos_config_id>/<device_type>', auth='public', type='json', website=True)
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

        return {'order': order_sudo.read(order_sudo._load_pos_data_fields(pos_config.id), load=False), 'payment_status': status}

    @http.route('/pos-self-order/change-printer-status', auth='public', type='json', website=True)
    def change_printer_status(self, access_token, has_paper):
        pos_config = self._verify_pos_config(access_token)
        if has_paper != pos_config.has_paper:
            pos_config.write({'has_paper': has_paper})


    def _get_order_prices(self, lines):
        amount_untaxed = sum(lines.mapped('price_subtotal'))
        amount_total = sum(lines.mapped('price_subtotal_incl'))
        return amount_total, amount_untaxed

    # The first part will be the session_id of the order.
    # The second part will be the table_id of the order.
    # Last part the sequence number of the order.
    # INFO: This is allow a maximum of 999 tables and 9999 orders per table, so about ~1M orders per session.
    # Example: 'Self-Order 00001-001-0001'
    def _generate_unique_id(self, pos_session_id, config_id, sequence_number, device_type):
        first_part = "{:05d}".format(int(pos_session_id))
        second_part = "{:03d}".format(int(config_id))
        third_part = "{:04d}".format(int(sequence_number))

        device = "Kiosk" if device_type == "kiosk" else "Self-Order"
        return f"{device} {first_part}-{second_part}-{third_part}"

    def _verify_pos_config(self, access_token):
        """
        Finds the pos.config with the given access_token and returns a record with reduced privileges.
        The record is has no sudo access and is in the context of the record's company and current pos.session's user.
        """
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not pos_config_sudo or (not pos_config_sudo.self_ordering_mode == 'mobile' and not pos_config_sudo.self_ordering_mode == 'kiosk') or not pos_config_sudo.has_active_session:
            raise Unauthorized("Invalid access token")
        company = pos_config_sudo.company_id
        user = pos_config_sudo.self_ordering_default_user_id
        return pos_config_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)

    def _verify_authorization(self, access_token, table_identifier, takeaway):
        """
        Similar to _verify_pos_config but also looks for the restaurant.table of the given identifier.
        The restaurant.table record is also returned with reduced privileges.
        """
        pos_config = self._verify_pos_config(access_token)
        table_sudo = request.env["restaurant.table"].sudo().search([('identifier', '=', table_identifier)], limit=1)

        if not table_sudo and not pos_config.self_ordering_mode == 'kiosk' and pos_config.self_ordering_service_mode == 'table' and not takeaway:
            raise Unauthorized("Table not found")

        company = pos_config.company_id
        user = pos_config.self_ordering_default_user_id
        table = table_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)
        return pos_config, table

    def _check_records(self, pos_config, order):
        dynamic_models = pos_config._get_dynamic_models()
        pos_order_model = pos_config.env['pos.order']

        def check_vals_dict(vals, parent_model):
            """Recursively check a values dictionary for whitelisted models."""
            for field_name, value in vals.items():
                # Skip if not a list or empty
                if not isinstance(value, list) or not value:
                    continue

                # Check if first item is a command tuple
                if not isinstance(value[0], (list, tuple)):
                    continue

                # Skip if field doesn't exist
                field = parent_model._fields.get(field_name)
                if not field or not field.relational:
                    continue

                # Get comodel_name
                comodel_name = field.comodel_name
                for command in value:
                    if not isinstance(command, (list, tuple)) or not command:
                        continue

                    cmd_type = command[0]

                    # Only validate create (0), update (1), and delete (2) commands
                    # Link (4), unlink (3), unlink all (5), and replace (6) are allowed for any model
                    if cmd_type in (Command.CREATE, Command.UPDATE, Command.DELETE) and comodel_name not in dynamic_models:
                        raise Unauthorized(_(
                            "You are not authorized to create, update, or delete records of type '%(model)s'. "
                            "Only the following models are allowed: %(allowed)s",
                            model=comodel_name,
                            allowed=', '.join(dynamic_models),
                        ))

                    # For create (0) and update (1), recursively check nested values
                    if cmd_type in (Command.CREATE, Command.UPDATE) and len(command) >= 3 and isinstance(command[2], dict):
                        nested_model = pos_config.env[comodel_name] if comodel_name else parent_model
                        check_vals_dict(command[2], nested_model)

        # Start validation from the order dict
        check_vals_dict(order, pos_order_model)
