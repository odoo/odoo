# -*- coding: utf-8 -*-
import re
from datetime import timedelta
from odoo import http, fields
from odoo.http import request
from odoo.tools import float_round
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized

class PosSelfOrderController(http.Controller):
    @http.route("/pos-self-order/process-order/<device_type>/", auth="public", type="json", website=True)
    def process_order(self, order, access_token, table_identifier, device_type):
        is_takeaway = order.get('takeaway')
        pos_config, table = self._verify_authorization(access_token, table_identifier, is_takeaway)
        pos_session = pos_config.current_session_id

        # Create the order
        ir_sequence_session = pos_config.env['ir.sequence'].with_context(company_id=pos_config.company_id.id).next_by_code(f'pos.order_{pos_session.id}')
        sequence_number = re.findall(r'\d+', ir_sequence_session)[0]
        order_reference = self._generate_unique_id(pos_session.id, pos_config.id, sequence_number, device_type)
        fiscal_position = (
            pos_config.takeaway_fp_id
            if is_takeaway
            else pos_config.default_fiscal_position_id
        )

        if 'picking_type_id' in order:
            del order['picking_type_id']

        order['name'] = order_reference
        order['pos_reference'] = order_reference
        order['sequence_number'] = sequence_number
        order['user_id'] = request.session.uid
        order['date_order'] = str(fields.Datetime.now())
        order['fiscal_position_id'] = fiscal_position.id if fiscal_position else False

        results = pos_config.env['pos.order'].sudo().with_context(from_self=True).with_company(pos_config.company_id.id).sync_from_ui([order])
        line_ids = pos_config.env['pos.order.line'].browse([line['id'] for line in results['pos.order.line']])
        order_ids = pos_config.env['pos.order'].browse([order['id'] for order in results['pos.order']])

        self._verify_line_price(line_ids, pos_config)

        amount_total, amount_untaxed = self._get_order_prices(order_ids.lines)
        order_ids.write({
            'state': 'paid' if amount_total == 0 else 'draft',
            'amount_tax': amount_total - amount_untaxed,
            'amount_total': amount_total,
        })

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
        pricelist = pos_config.pricelist_id
        sale_price_digits = pos_config.env['decimal.precision'].precision_get('Product Price')

        for line in lines:
            product = line.product_id
            lst_price = pricelist._get_product_price(product, quantity=line.qty) if pricelist else product.lst_price
            selected_attributes = line.attribute_value_ids
            lst_price += sum(selected_attributes.mapped('price_extra'))
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            lst_price += price_extra

            fiscal_pos = pos_config.default_fiscal_position_id
            if takeaway and pos_config.takeaway_fp_id:
                fiscal_pos = pos_config.takeaway_fp_id

            if len(line.combo_line_ids) > 0:
                original_total = sum(line.combo_line_ids.mapped("combo_item_id").combo_id.mapped("base_price"))
                remaining_total = lst_price
                factor = lst_price / original_total if original_total > 0 else 1

                for i, pos_order_line in enumerate(line.combo_line_ids):
                    child_product = pos_order_line.product_id
                    price_unit = float_round(pos_order_line.combo_id.base_price * factor, precision_digits=sale_price_digits)
                    remaining_total -= price_unit

                    if i == len(line.combo_line_ids) - 1:
                        price_unit += remaining_total

                    selected_attributes = pos_order_line.attribute_value_ids
                    price_extra_child = sum(attr.price_extra for attr in selected_attributes)
                    price_unit += pos_order_line.combo_item_id.extra_price + price_extra_child

                    taxes = fiscal_pos.map_tax(child_product.taxes_id) if fiscal_pos else child_product.taxes_id
                    pdetails = taxes.compute_all(price_unit, pos_config.currency_id, pos_order_line.qty, child_product)

                    pos_order_line.write({
                        'price_unit': price_unit,
                        'price_subtotal': pdetails.get('total_excluded'),
                        'price_subtotal_incl': pdetails.get('total_included'),
                        'price_extra': price_extra_child,
                        'tax_ids': child_product.taxes_id,
                    })
                lst_price = 0

    @http.route('/pos-self-order/get-orders', auth='public', type='json', website=True)
    def get_orders_by_access_token(self, access_token, order_access_tokens):
        pos_config = self._verify_pos_config(access_token)
        session = pos_config.current_session_id
        orders = session.order_ids.filtered_domain([
            ("access_token", "in", order_access_tokens),
            ("date_order", ">=", fields.Datetime.now() - timedelta(days=7)),
        ])

        if not orders:
            return {}

        return self._generate_return_values(orders, pos_config)

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
