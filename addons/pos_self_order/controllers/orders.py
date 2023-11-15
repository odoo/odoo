# -*- coding: utf-8 -*-

from datetime import timedelta
import uuid
from odoo import http, fields, Command
from odoo.http import request
from odoo.addons.pos_self_order.controllers.utils import reduce_privilege
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized

class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-new-order", auth="public", type="json", website=True)
    def process_new_order(self, order, access_token, table_identifier):
        lines = order.get('lines')
        pos_config, table = self._verify_authorization(access_token, table_identifier)
        pos_session = pos_config.current_session_id
        sequence_number = self._get_sequence_number(table.id, pos_session.id)
        unique_id = self._generate_unique_id(pos_session.id, table.id, sequence_number)

        # Create the order without lines and prices computed
        # We need to remap the order because some required fields are not used in the frontend.
        order = {
            'id': unique_id,
            'data': {
                'uuid': order.get('uuid'),
                'name': unique_id,
                'user_id': request.session.uid,
                'sequence_number': sequence_number,
                'access_token': uuid.uuid4().hex,
                'pos_session_id': pos_session.id,
                'table_id': table.id if table else False,
                'partner_id': False,
                'creation_date': str(fields.Datetime.now()),
                'fiscal_position_id': pos_config.default_fiscal_position_id.id,
                'statement_ids': [],
                'lines': [],
                'amount_tax': 0,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_return': 0,
            },
            'to_invoice': False,
            'session_id': pos_session.id,
        }

        # Save the order in the database to get the id
        posted_order_id = pos_config.env['pos.order'].create_from_ui([order], draft=True)[0].get('id')

        # Process the lines and get their prices computed
        lines = self._process_lines(lines, pos_config, posted_order_id)

        # Compute the order prices
        amount_total, amount_untaxed = self._get_order_prices(lines)

        # Update the order with the computed prices and lines
        order = pos_config.env["pos.order"].browse(posted_order_id)
        order.write({
            'lines': [Command.create(line) for line in lines],
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        return order._export_for_self_order()

    @http.route('/pos-self-order/get-orders-taxes', auth='public', type='json', website=True)
    def get_order_taxes(self, order, access_token):
        pos_config = self._verify_pos_config(access_token)
        lines = self._process_lines(order.get('lines'), pos_config, 0)
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
    def update_existing_order(self, order, access_token, table_identifier):
        order_id = order.get('id')
        order_access_token = order.get('access_token')
        pos_config, table = self._verify_authorization(access_token, table_identifier)
        session = pos_config.current_session_id

        pos_order = session.order_ids.filtered_domain([
            ('id', '=', order_id),
            ('access_token', '=', order_access_token),
            ('table_id', '=', table.id)
        ])

        if not pos_order:
            raise Unauthorized("Order not found in the server !")
        elif pos_order.state != 'draft':
            raise Unauthorized("Order is not in draft state")

        lines = self._process_lines(order.get('lines'), pos_config, pos_order.id)
        for line in lines:
            if line.get('id'):
                order_line = pos_order.lines.browse(line.get('id'))

                if line.get('qty') < order_line.qty:
                    line.set('qty', order_line.qty)

                order_line.write({
                    **line,
                })
            else:
                pos_order.lines.create(line)

        amount_total, amount_untaxed = self._get_order_prices(lines)
        pos_order.write({
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        return pos_order._export_for_self_order()

    @http.route('/pos-self-order/get-orders', auth='public', type='json', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens):
        pos_config = self._verify_pos_config(access_token)
        session = pos_config.current_session_id
        orders = session.order_ids.filtered_domain([
            ("access_token", "in", order_access_tokens),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=7)),
        ])

        if not orders:
            raise NotFound("Orders not found")

        result = []
        for order in orders:
            result.append(order._export_for_self_order())

        return result

    @http.route('/pos-self-order/get-tables', auth='public', type='json', website=True)
    def get_tables(self, access_token):
        pos_config = self._verify_pos_config(access_token)
        tables = pos_config.floor_ids.table_ids.filtered(lambda t: t.active).read(['id', 'name', 'identifier', 'floor_id'])

        for table in tables:
            table['floor_name'] = table.get('floor_id')[1]

        return tables

    def _get_price_extra(self, product, selected_attributes):
        price_extra = 0
        for attribute in product.attribute_line_ids:
            if attribute.display_name in selected_attributes:
                attribute_value_name = selected_attributes[attribute.display_name]
                value_ids = attribute.product_template_value_ids.filtered(lambda v: v.name == attribute_value_name)
                price_extra += value_ids[0].price_extra
        return price_extra

    def _process_lines(self, lines, pos_config, pos_order_id):
        newLines = []
        pricelist = pos_config.pricelist_id

        for line in lines:
            product = pos_config.env['product.product'].browse(line.get('product_id'))
            price_unit = pricelist._get_product_price(product, quantity=line.get('qty')) if pricelist else product.lst_price

            if line.get('selected_attributes'):
                price_extra = self._get_price_extra(product, line.get('selected_attributes'))
                price_unit += price_extra

            config_fiscal_pos = pos_config.default_fiscal_position_id
            selected_account_tax = config_fiscal_pos.map_tax(product.taxes_id) if config_fiscal_pos else product.taxes_id

            tax_results = selected_account_tax.compute_all(
                price_unit,
                pos_config.currency_id,
                line.get('qty'),
                product,
            )

            newLines.append({
                'price_unit': price_unit,
                'price_subtotal': tax_results.get('total_excluded'),
                'price_subtotal_incl': tax_results.get('total_included'),
                'price_extra': 0,
                'id': line.get('id'),
                'order_id': pos_order_id,
                'tax_ids': product.taxes_id,
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
    # The second part will be the table_id of the order.
    # Last part the sequence number of the order.
    # INFO: This is allow a maximum of 999 tables and 9999 orders per table, so about ~1M orders per session.
    # Example: 'Self-Order 00001-001-0001'
    def _generate_unique_id(self, pos_session_id: int, table_id: int, sequence_number: int) -> str:
        first_part = "{:05d}".format(int(pos_session_id))
        second_part = "{:03d}".format(int(table_id))
        third_part = "{:04d}".format(int(sequence_number))

        return f"Self-Order {first_part}-{second_part}-{third_part}"

    def _get_sequence_number(self, table_id, session_id):
        order_sudo = request.env["pos.order"].sudo().search([(
            'pos_reference',
            'like',
            f"Self-Order {session_id:0>5}-{table_id:0>3}")], order='id desc', limit=1)

        return (order_sudo.sequence_number + 1) or 1

    def _verify_pos_config(self, access_token):
        """
        Finds the pos.config with the given access_token and returns a record with reduced privileges.
        The record is has no sudo access and is in the context of the record's company and current pos.session's user.
        """
        pos_config_sudo = request.env['pos.config'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not pos_config_sudo or not pos_config_sudo.self_order_table_mode or not pos_config_sudo.has_active_session:
            raise Unauthorized("Invalid access token")
        company = pos_config_sudo.company_id
        user = pos_config_sudo.current_session_id.user_id
        return reduce_privilege(pos_config_sudo, company, user)

    def _verify_authorization(self, access_token, table_identifier):
        """
        Similar to _verify_pos_config but also looks for the restaurant.table of the given identifier.
        The restaurant.table record is also returned with reduced privileges.
        """
        table_sudo = request.env["restaurant.table"].sudo().search([('identifier', '=', table_identifier)], limit=1)
        if not table_sudo:
            raise Unauthorized("Table not found")

        pos_config = self._verify_pos_config(access_token)
        company = pos_config.company_id
        user = pos_config.current_session_id.user_id
        table = reduce_privilege(table_sudo, company, user)
        return pos_config, table
