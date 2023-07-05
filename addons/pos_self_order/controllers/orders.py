# -*- coding: utf-8 -*-

from datetime import timedelta
import uuid
from odoo import http, fields, Command
from odoo.http import request
from werkzeug.exceptions import NotFound, Unauthorized

class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-new-order", auth="public", type="json", website=True)
    def process_new_order(self, order, access_token):
        lines = order.get('lines')

        pos_config_sudo = self._verify_authorization(access_token)
        pos_session_sudo = pos_config_sudo.current_session_id
        sequence_number = self._get_sequence_number(pos_session_sudo.id)
        unique_id = self._generate_unique_id(pos_session_sudo.id, sequence_number)

        # Create the order without lines and prices computed
        # We need to remap the order because some required fields are not used in the frontend.
        order = self._prepare_order_data(unique_id, order, pos_session_sudo, sequence_number, pos_config_sudo)

        # Save the order in the database to get the id
        posted_order_id = request.env['pos.order'].sudo().create_from_ui([order], draft=True)[0].get('id')

        # Process the lines and get their prices computed
        lines = self._process_lines(lines, pos_config_sudo, posted_order_id)

        # Compute the order prices
        amount_total, amount_untaxed = self._get_order_prices(lines)

        # Update the order with the computed prices and lines
        order_sudo = request.env["pos.order"].sudo().browse(posted_order_id)
        order_sudo.write({
            'lines': [Command.create(line) for line in lines],
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        return order_sudo._export_for_self_order()

    def _prepare_order_data(self, unique_id, order, pos_session_sudo, sequence_number, pos_config_sudo):
        return {
            'id': unique_id,
            'data': {
                'uuid': order.get('uuid'),
                'name': unique_id,
                'user_id': request.session.uid,
                'sequence_number': sequence_number,
                'access_token': uuid.uuid4().hex,
                'pos_session_id': pos_session_sudo.id,
                'partner_id': False,
                'creation_date': str(fields.Datetime.now()),
                'fiscal_position_id': pos_config_sudo.default_fiscal_position_id,
                'statement_ids': [],
                'lines': [],
                'amount_tax': 0,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_return': 0,
            },
            'to_invoice': False,
            'session_id': pos_session_sudo.id,
        }

    @http.route('/pos-self-order/get-orders-taxes', auth='public', type='json', website=True)
    def get_order_taxes(self, order, access_token):
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not pos_config_sudo or not pos_config_sudo.self_order_ordering_mode or not pos_config_sudo.has_active_session:
            raise Unauthorized("Invalid access token")

        lines = self._process_lines(order.get('lines'), pos_config_sudo, 0)
        amount_total, amount_untaxed = self._get_order_prices(lines)

        return {
            'lines': [{
                'uuid': line.get('uuid'),
                'price_subtotal': line.get('price_subtotal'),
                'price_subtotal_incl': line.get('price_subtotal_incl'),
            } for line in lines],
            'amount_total': amount_total,
            'amount_tax': amount_total - amount_untaxed,
        }

    @http.route('/pos-self-order/update-existing-order', auth="public", type="json", website=True)
    def update_existing_order(self, order, access_token):
        order_id = order.get('id')
        order_access_token = order.get('access_token')
        pos_config_sudo = self._verify_authorization(access_token)

        order_sudo = request.env['pos.order'].sudo().search([
            ('id', '=', order_id),
            ('access_token', '=', order_access_token),
        ])

        if not order_sudo:
            raise Unauthorized("Order not found in the server !")
        elif order_sudo.state != 'draft':
            raise Unauthorized("Order is not in draft state")

        lines = self._process_lines(order.get('lines'), pos_config_sudo, order_sudo.id)
        for line in lines:
            if line.get('id'):
                line_sudo = order_sudo.lines.filtered(lambda l: l.id == line.get('id'))

                if line.get('qty') < line_sudo.qty:
                    line.set('qty', line_sudo.qty)

                line_sudo.write({
                    **line,
                })
            else:
                order_sudo.lines.create(line)

        amount_total, amount_untaxed = self._get_order_prices(lines)
        order_sudo.write({
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        return order_sudo._export_for_self_order()

    @http.route('/pos-self-order/get-orders', auth='public', type='json', website=True)
    def get_orders_by_access_token(self, order_access_tokens):
        orders_sudo = request.env["pos.order"].sudo().search([
            ("access_token", "in", order_access_tokens),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=7)),
        ])

        if not orders_sudo:
            raise NotFound("Orders not found")

        orders = []
        for order in orders_sudo:
            orders.append(order._export_for_self_order())

        return orders

    def _process_lines(self, lines, pos_config_sudo, pos_order_id):
        newLines = []
        pricelist = request.env['product.pricelist'].sudo().browse(pos_config_sudo.pricelist_id.id)

        for line in lines:
            product_sudo = request.env["product.product"].sudo().browse(int(line.get("product_id")))
            # todo take into account the price extra
            price_unit = pricelist._get_product_price(product_sudo, quantity=1) if pricelist else product_sudo.lst_price

            config_fiscal_pos = pos_config_sudo.default_fiscal_position_id
            selected_account_tax = config_fiscal_pos.map_tax(product_sudo.taxes_id) if config_fiscal_pos else product_sudo.taxes_id

            tax_results = selected_account_tax.compute_all(
                price_unit,
                pos_config_sudo.currency_id,
                line.get('qty'),
                product_sudo,
            )

            newLines.append({
                'price_unit': price_unit,
                'price_subtotal': tax_results.get('total_excluded'),
                'price_subtotal_incl': tax_results.get('total_included'),
                'price_extra': 0,
                'id': line.get('id'),
                'order_id': pos_order_id,
                'tax_ids': product_sudo.taxes_id,
                'uuid': line.get('uuid'),
                'product_id': line.get('product_id'),
                'qty': line.get('qty'),
                'customer_note': line.get('customer_note'),
                'selected_attributes': line.get('selected_attributes'),
                'full_product_name': line.get('full_product_name'),
            })

        return newLines

    def _get_order_prices(self, lines):
        amount_untaxed = sum([line.get('price_subtotal') for line in lines])
        amount_total = sum([line.get('price_subtotal_incl') for line in lines])
        return amount_total, amount_untaxed

    # The first part will be the session_id of the order.
    # The second part needs to be found
    # Last part the sequence number of the order.
    # Example: 'Self-Order 00001-001-0001'
    def _generate_unique_id(self, pos_session_id: int, sequence_number: int) -> str:
        first_part = "{:05d}".format(int(pos_session_id))
        third_part = "{:04d}".format(int(sequence_number))

        return f"Self-Order {first_part}-000-{third_part}"

    def _get_sequence_number(self, session_id):
        order_sudo = request.env["pos.order"].sudo().search([(
            'pos_reference',
            'like',
            f"Self-Order {session_id:0>5}-000-")], order='id desc', limit=1)

        return (order_sudo.sequence_number + 1) or 1

    def _verify_authorization(self, access_token):
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not pos_config_sudo or not pos_config_sudo.self_order_ordering_mode or not pos_config_sudo.has_active_session:
            raise Unauthorized("Invalid access token")

        return pos_config_sudo
