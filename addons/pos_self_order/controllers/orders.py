# -*- coding: utf-8 -*-
import re
import uuid
from functools import partial
from datetime import timedelta
from odoo import http, fields, _
from odoo.http import request
from odoo.tools import float_round
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized
from odoo.exceptions import MissingError
from odoo.tools import consteq

class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-new-order/<device_type>/", auth="public", type="json", website=True)
    def process_new_order(self, order, access_token, table_identifier, device_type):
        lines = order.get('lines')
        is_take_away = order.get('take_away')
        pos_config, table = self._verify_authorization(access_token, table_identifier, is_take_away)
        pos_session = pos_config.current_session_id
        ir_sequence_session = pos_config.env['ir.sequence'].with_context(company_id=pos_config.company_id.id).next_by_code(f'pos.order_{pos_session.id}')

        sequence_number = re.findall(r'\d+', ir_sequence_session)[0]
        order_reference = self._generate_unique_id(pos_session.id, pos_config.id, sequence_number, device_type)

        fiscal_position = (
            pos_config.self_ordering_alternative_fp_id
            if is_take_away
            else pos_config.default_fiscal_position_id
        )

        # Create the order without lines and prices computed
        # We need to remap the order because some required fields are not used in the frontend.
        order = {
            'data': {
                'name': order_reference,
                'sequence_number': sequence_number,
                'uuid': order.get('uuid'),
                'take_away': order.get('take_away'),
                'user_id': request.session.uid,
                'access_token': uuid.uuid4().hex,
                'pos_session_id': pos_session.id,
                'table_id': table.id if table else False,
                'partner_id': False,
                'date_order': str(fields.Datetime.now()),
                'fiscal_position_id': fiscal_position.id,
                'statement_ids': [],
                'lines': [],
                'amount_tax': 0,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_return': 0,
                'table_stand_number': order.get('table_stand_number'),
                'ticket_code': order.get('ticket_code'),
                'pricelist_id': pos_config.pricelist_id.id if pos_config.pricelist_id else False
            },
            'to_invoice': False,
            'session_id': pos_session.id,
        }

        # Save the order in the database to get the id
        posted_order_id = pos_config.env['pos.order'].with_context(from_self=True).create_from_ui([order], draft=True)[0].get('id')

        # Process the lines and get their prices computed
        processed_lines = self._process_lines(lines, pos_config, posted_order_id, is_take_away)

        # Compute the order prices
        amount_total, amount_untaxed = self._get_order_prices(processed_lines)

        # Update the order with the computed prices and lines
        saved_order = pos_config.env["pos.order"].browse(posted_order_id)
        saved_lines = pos_config.env['pos.order.line'].with_user(pos_config.self_ordering_default_user_id).create(processed_lines)

        saved_order.write({
            'lines': saved_lines,
            'state': 'paid' if amount_total == 0 else 'draft',
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

        order['data']['lines'] = lines
        self._process_combo_items(saved_order, order['data'])
        saved_order.send_table_count_notification(saved_order.table_id)
        return saved_order._export_for_self_order()

    @http.route('/pos-self-order/get-orders-taxes', auth='public', type='json', website=True)
    def get_order_taxes(self, order, access_token):
        pos_config = self._verify_pos_config(access_token)
        lines = self._process_lines(order.get('lines'), pos_config, 0, order.get('take_away'))
        amount_total, amount_untaxed = self._get_order_prices(lines)

        return {
            'lines': [{
                'uuid': line.get('uuid'),
                'price_unit': line.get('price_unit'),
                'price_extra': line.get('price_extra'),
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
        pos_config, table = self._verify_authorization(access_token, table_identifier, order.get('take_away'))
        session = pos_config.current_session_id

        pos_order = session.order_ids.filtered_domain([
            ('id', '=', order_id),
            ('access_token', '=', order_access_token),
        ])

        if not pos_order:
            raise Unauthorized("Order not found in the server !")
        elif pos_order.state != 'draft':
            raise Unauthorized("Order is not in draft state")

        lines = self._process_lines(order.get('lines'), pos_config, pos_order.id, order.get('take_away'))
        for line in lines:
            if line.get('id'):
                # we need to find by uuid because each time we update the order, id of orderlines changed.
                order_line = pos_order.lines.filtered(lambda l: l.uuid == line.get('uuid'))

                if line.get('qty') < order_line.qty:
                    line.set('qty', order_line.qty)

                if order_line:
                    order_line.write({
                        **line,
                    })
            else:
                pos_order.lines.create(line)

        amount_total, amount_untaxed = self._get_order_prices(lines)
        pos_order.write({
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
            'table_id': table if table else False,
            'table_stand_number': order.get('table_stand_number'),
        })

        self._process_combo_items(pos_order, order)
        pos_order.send_table_count_notification(pos_order.table_id)
        return pos_order._export_for_self_order()

    def _process_combo_items(self, order, order_values):
        """
            Here we need to process original order dict to add
            combo_line_ids and combo_parent_id to the lines
            and then call the _link_combo_items method to link
            the combo lines together.
        """
        combo_lines = []
        lines = order_values.get('lines')
        for line in lines:
            if line.get('child_lines'):
                line['combo_line_ids'] = [child_line['uuid'] for child_line in line['child_lines']]
            elif line.get('combo_parent_uuid'):
                line['combo_parent_id'] = line.get('combo_parent_uuid')

            if line.get('combo_line_ids') or line.get('combo_parent_id'):
                combo_lines.append([0, 0, line])

        order_values['lines'] = combo_lines
        order._link_combo_items(order_values)

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
    def get_orders_by_access_token(self, access_token, order_access_tokens):
        pos_config = self._verify_pos_config(access_token)
        session = pos_config.current_session_id
        orders = session.order_ids.filtered_domain([
            ("access_token", "in", order_access_tokens),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=7)),
        ])

        if not orders:
            raise NotFound("Orders not found")

        orders_for_ui = []
        for order in orders:
            orders_for_ui.append(order._export_for_self_order())

        return orders_for_ui

    @http.route('/pos-self-order/get-tables', auth='public', type='json', website=True)
    def get_tables(self, access_token):
        pos_config = self._verify_pos_config(access_token)
        tables = pos_config.floor_ids.table_ids.filtered(lambda t: t.active).read(['id', 'name', 'identifier', 'floor_id'])

        for table in tables:
            table['floor_name'] = table.get('floor_id')[1]

        return tables


    @http.route('/kiosk/payment/<int:pos_config_id>/<device_type>', auth='public', type='json', website=True)
    def pos_self_order_kiosk_payment(self, pos_config_id, order, payment_method_id, access_token, device_type):
        pos_config = self._verify_pos_config(access_token)
        order_dict = self.process_new_order(order, access_token, None, device_type)

        if not order_dict.get('id'):
            raise BadRequest("Something went wrong")

        # access_token verified in process_new_order
        order_sudo = pos_config.env['pos.order'].browse(order_dict.get('id'))
        payment_method_sudo = pos_config.env["pos.payment.method"].browse(payment_method_id)
        if not order_sudo or not payment_method_sudo or payment_method_sudo not in order_sudo.config_id.payment_method_ids:
            raise NotFound("Order or payment method not found")

        status = payment_method_sudo._payment_request_from_kiosk(order_sudo)

        if not status:
            raise BadRequest("Something went wrong")

        return {'order': order_sudo._export_for_self_order(), 'payment_status': status}

    def _process_lines(self, lines, pos_config, pos_order_id, take_away=False):
        appended_uuid = []
        newLines = []
        pricelist = pos_config.pricelist_id
        sale_price_digits = pos_config.env['decimal.precision'].precision_get('Product Price')
        process_line = partial(pos_config.env['pos.order.line']._order_line_fields, session_id=pos_config.current_session_id.id)

        combo_line_ids = [line['combo_line_id'] for line in lines if line.get('combo_line_id')]
        combo_lines = pos_config.env['pos.combo.line'].search([('id', 'in', combo_line_ids)])
        attribute_value_ids = sum([line.get('attribute_value_ids', []) for line in lines], [])
        fetched_attributes = pos_config.env['product.template.attribute.value'].search([('id', 'in', attribute_value_ids)])

        fiscal_pos = pos_config.default_fiscal_position_id

        if take_away and pos_config.self_ordering_alternative_fp_id:
            fiscal_pos = pos_config.self_ordering_alternative_fp_id

        for line in lines:
            if line.get('uuid') in appended_uuid or not line.get('product_id'):
                continue

            line_qty = line.get('qty')
            product = pos_config.env['product.product'].browse(int(line.get('product_id')))
            lst_price = pricelist._get_product_price(product, quantity=line_qty) if pricelist else product.lst_price
            selected_attributes = fetched_attributes.browse(line.get('attribute_value_ids', []))
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            lst_price += price_extra

            children = [l for l in lines if l.get('combo_parent_uuid') == line.get('uuid')]
            pos_combo_lines = combo_lines.browse([child.get('combo_line_id') for child in children])

            newLines.append({})
            if len(children) > 0:
                original_total = sum(pos_combo_lines.mapped("combo_id.base_price"))
                remaining_total = lst_price
                factor = lst_price / original_total

                for i, child in enumerate(children):
                    child_product = pos_config.env['product.product'].browse(int(child.get('product_id')))
                    pos_combo_line = pos_combo_lines.browse(child.get('combo_line_id'))
                    price_unit = float_round(pos_combo_line.combo_id.base_price * factor, precision_digits=sale_price_digits)
                    remaining_total -= price_unit
                    if i == len(children) - 1:
                        price_unit += remaining_total

                    selected_attributes = fetched_attributes.browse(child.get('attribute_value_ids', []))
                    price_extra_child = sum(attr.price_extra for attr in selected_attributes)
                    price_unit += pos_combo_line.combo_price + price_extra_child

                    price_unit_fp = child_product._get_price_unit_after_fp(price_unit, pos_config.currency_id, fiscal_pos)
                    taxes = fiscal_pos.map_tax(child_product.taxes_id) if fiscal_pos else child_product.taxes_id
                    pdetails = taxes.compute_all(price_unit_fp, pos_config.currency_id, line_qty, child_product)

                    newLines.append({
                        'price_unit': price_unit_fp,
                        'price_subtotal': pdetails.get('total_excluded'),
                        'price_subtotal_incl': pdetails.get('total_included'),
                        'custom_attribute_value_ids': [[0, 0, cAttr] for cAttr in child.get('custom_attribute_value_ids')] if child.get('custom_attribute_value_ids') else [],
                        'id': child.get('id'),
                        'order_id': pos_order_id,
                        'tax_ids': child_product.taxes_id,
                        'uuid': child.get('uuid'),
                        'product_id': child.get('product_id'),
                        'qty': child.get('qty'),
                        'customer_note': child.get('customer_note'),
                        'attribute_value_ids': child.get('attribute_value_ids') or [],
                        'full_product_name': child.get('full_product_name'),
                        'combo_parent_uuid': child.get('combo_parent_uuid'),
                        'combo_id': child.get('combo_id'),
                        'price_extra': price_extra_child
                    })
                    appended_uuid.append(child.get('uuid'))

                lst_price = 0

            price_unit_fp = product._get_price_unit_after_fp(lst_price, pos_config.currency_id, fiscal_pos)
            taxes_after_fp = fiscal_pos.map_tax(product.taxes_id) if fiscal_pos else product.taxes_id
            pdetails = taxes_after_fp.compute_all(price_unit_fp, pos_config.currency_id, line_qty, product)

            newLine = {
                'price_unit': price_unit_fp,
                'price_subtotal': pdetails.get('total_excluded'),
                'price_subtotal_incl': pdetails.get('total_included'),
                'id': line.get('id'),
                'order_id': pos_order_id,
                'tax_ids': product.taxes_id,
                'uuid': line.get('uuid'),
                'product_id': line.get('product_id'),
                'qty': line_qty,
                'customer_note': line.get('customer_note'),
                'attribute_value_ids': line.get('attribute_value_ids') or [],
                'custom_attribute_value_ids': [[0, 0, cAttr] for cAttr in line.get('custom_attribute_value_ids')] if line.get('custom_attribute_value_ids') else [],
                'full_product_name': line.get('full_product_name'),
                'combo_parent_uuid': line.get('combo_parent_uuid'),
                'combo_id': line.get('combo_id'),
                'price_extra': price_extra
            }
            newLines[len(newLines) - 1 - len(children)] = newLine
            appended_uuid.append(line.get('uuid'))

        sanatized_lines = [process_line([0, 0, line])[2] for line in newLines]
        return sanatized_lines

    def _get_order_prices(self, lines):
        amount_untaxed = sum([line.get('price_subtotal') for line in lines])
        amount_total = sum([line.get('price_subtotal_incl') for line in lines])
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

    def _verify_authorization(self, access_token, table_identifier, take_away):
        """
        Similar to _verify_pos_config but also looks for the restaurant.table of the given identifier.
        The restaurant.table record is also returned with reduced privileges.
        """
        pos_config = self._verify_pos_config(access_token)
        table_sudo = request.env["restaurant.table"].sudo().search([('identifier', '=', table_identifier)], limit=1)

        if not table_sudo and not pos_config.self_ordering_mode == 'kiosk' and pos_config.self_ordering_service_mode == 'table' and not take_away:
            raise Unauthorized("Table not found")

        company = pos_config.company_id
        user = pos_config.self_ordering_default_user_id
        table = table_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids)
        return pos_config, table
