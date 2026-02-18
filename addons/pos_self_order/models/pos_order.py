# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models, fields, api
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_id = fields.Many2one('product.combo', string='Combo reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('combo_parent_uuid')):
                vals.update([
                    ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
                ])
            if 'combo_parent_uuid' in vals:
                del vals['combo_parent_uuid']
        return super().create(vals_list)

    def write(self, vals):
        if (vals.get('combo_parent_uuid')):
            vals.update([
                ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
            ])
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
        return super().write(vals)

class PosOrder(models.Model):
    _inherit = "pos.order"

    table_stand_number = fields.Char(string="Table Stand Number")

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('id', '=', False)]

    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        result = super().sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in result['pos.order'] if order.get('id')])
        self._send_notification(order_ids)
        return result

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config.notify_synchronisation(config.current_session_id.id, self.env.context.get('login_number', 0))
            config._notify('ORDER_STATE_CHANGED', {})

    @api.model
    def _ensure_link_or_unlink(self, commands=[]):
        data = []
        for command in commands:
            if command[0] in [Command.LINK, Command.UNLINK] and isinstance(command[1], int):
                data.append(command)
        return data

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line):
        existing_order = pos_config.env['pos.order'].browse(order.get('id'))
        existing_lines = existing_order.lines if existing_order.exists() else pos_config.env['pos.order.line']

        if line[0] == Command.DELETE and line[1] in existing_lines.ids:
            return [Command.DELETE, line[1]]
        if line[0] == Command.UNLINK and line[1] in existing_lines.ids:
            return [Command.UNLINK, line[1]]
        if line[0] == Command.CREATE or line[0] == Command.UPDATE:
            line_data = line[2]

            if line_data.get('combo_line_ids'):
                # Special mapping processed in sync_from_ui, this relation doesn't contains commands.
                all_available_line_ids = [line[2].get('id') for line in order.get('lines') if line[0] in [Command.CREATE, Command.UPDATE] and line[2].get('combo_parent_id')]
                line_data['combo_line_ids'] = [id for id in line_data.get('combo_line_ids') if id in all_available_line_ids]

            return [Command.CREATE, 0, {
                'product_id': line_data.get('product_id'),
                'combo_id': line_data.get('combo_id'),
                'attribute_value_ids': self._ensure_link_or_unlink(line_data.get('attribute_value_ids')),
                'price_unit': line_data.get('price_unit'),
                'qty': line_data.get('qty'),
                'price_subtotal': line_data.get('price_subtotal'),
                'price_subtotal_incl': line_data.get('price_subtotal_incl'),
                'price_extra': line_data.get('price_extra'),
                'price_type': line_data.get('price_type'),
                'full_product_name': line_data.get('full_product_name'),
                'customer_note': line_data.get('customer_note'),
                'uuid': line_data.get('uuid'),
                'id': line_data.get('id'),
                'order_id': existing_order.id if existing_order.exists() else None,
                'combo_parent_id': line_data.get('combo_parent_id'),
                'combo_item_id': line_data.get('combo_item_id'),
                'combo_line_ids': line_data.get('combo_line_ids'),
            }]
        return []

    @api.model
    def _check_pos_order(self, pos_config, order):
        company = pos_config.company_id

        return {
            'id': order.get('id'),
            'access_token': order.get('access_token'),
            'name': order.get('name'),
            'table_id': order.get('table_id', False),
            'customer_count': order.get('customer_count', 0),
            'takeaway': order.get('takeaway', False),
            'table_stand_number': order.get('table_stand_number'),
            'last_order_preparation_change': order.get('last_order_preparation_change'),
            'date_order': order.get('date_order'),
            'amount_difference': order.get('amount_difference'),
            'amount_tax': order.get('amount_tax'),
            'amount_total': order.get('amount_total'),
            'amount_paid': order.get('amount_paid'),
            'amount_return': order.get('amount_return'),
            'company_id': company.id,
            'pricelist_id': pos_config.pricelist_id.id,
            'partner_id': order.get('partner_id'),
            'sequence_number': order.get('sequence_number'),
            'session_id': pos_config.current_session_id.id,
            'fiscal_position_id': pos_config.takeaway_fp_id.id if order.get('takeaway', False) else pos_config.default_fiscal_position_id.id,
            'state': order.get('state'),
            'account_move': order.get('account_move'),
            'floating_order_name': order.get('floating_order_name'),
            'general_note': order.get('general_note'),
            'nb_print': order.get('nb_print'),
            'pos_reference': order.get('pos_reference'),
            'to_invoice': order.get('to_invoice'),
            'shipping_date': order.get('shipping_date'),
            'is_tipped': order.get('is_tipped'),
            'tip_amount': order.get('tip_amount'),
            'ticket_code': order.get('ticket_code'),
            'uuid': order.get('uuid'),
            'has_deleted_line': order.get('has_deleted_line'),
            'lines': [self._check_pos_order_lines(pos_config, order, line) for line in order.get('lines', [])],
        }
