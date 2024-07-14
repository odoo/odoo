# -*- coding: utf-8 -*-

from odoo import models, api
from itertools import groupby
from operator import itemgetter


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _check_config_germany_floor(self, session_id=None, order_id=None):
        """
        Check if the pos config is from a company located in Germany and if it has at least one floor
        The pos config is retrieved either by the session_id if the order has not been created yet,
        otherwise from an id of an order
        """
        config = None
        if session_id:
            config = self.env['pos.session'].browse(session_id).config_id
        elif order_id:
            config = self.browse(order_id).config_id
        return bool(config and config.company_id.l10n_de_is_germany_and_fiskaly() and config.floor_ids)

    @api.model
    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        if self._check_config_germany_floor(session_id=ui_order['pos_session_id']) and 'l10n_de_fiskaly_time_start' not in fields:
            fields['l10n_de_fiskaly_time_start'] = ui_order['date_order'].replace('T', ' ')[:19]
        return fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        if self._check_config_germany_floor(session_id=orders[0]['data']['pos_session_id']) and draft:
            order_differences = {}
            for ui_order in orders:
                existing_order = None
                if ui_order['data'].get('server_id'):
                    existing_order = self.env['pos.order'].browse(ui_order['data']['server_id']).exists()
                if not existing_order or existing_order.state == 'draft':
                    differences = self._line_differences(existing_order, ui_order['data'])
                    if differences:
                        order_differences[ui_order['data']['name']] = differences

            res = super().create_from_ui(orders, draft)
            for json_record in res:
                if json_record['pos_reference'] in order_differences:
                    json_record['differences'] = order_differences[json_record['pos_reference']]
            return res
        else:
            return super().create_from_ui(orders, draft)

    @api.model
    def _line_differences(self, existing_order, ui_order=None):
        """
        :param existing_order: actual PosOrder object
        :param ui_order: json order coming from the front end or None
        :return: a list of lines difference
        """
        new_line_dict = {} if not ui_order else self._merge_order_lines(
            [line[2] for line in ui_order['lines'] if line[2]['qty'] != 0]
        )
        old_lines = []
        if existing_order:
            old_lines = existing_order.lines.read(['qty', 'product_id', 'full_product_name', 'price_subtotal_incl',
                                                   'price_unit', 'discount'])
        for line in old_lines:
            line['product_id'] = line['product_id'][0]
        old_line_dict = self._merge_order_lines(old_lines)

        differences = []
        for new_line_key, new_line in new_line_dict.items():
            if new_line_key not in old_line_dict:
                differences.append(new_line)
            elif old_line_dict[new_line_key]['quantity'] != new_line['quantity']:
                # we could copy the dict but since it's not going to be used anymore we can just modify it
                new_line['quantity'] -= old_line_dict[new_line_key]['quantity']
                differences.append(new_line)

        for old_line_key, old_line in old_line_dict.items():
            if old_line_key not in new_line_dict:
                old_line['quantity'] = -old_line['quantity']
                differences.append(old_line)

        return differences

    @api.model
    def _merge_order_lines(self, order_lines):
        """
        It is possible to have multiple lines regarding the same product with the same unit price.
        This method will merge those lines into one. The lines with the same product but with different price or
        discount will be considered different.
        This method create a dictionary with the required information by triplet (id, price, discount).
        (note: the 'price_per_unit' is the full price of the product (vat + discount))
        :param order_lines: The list of lines in a dictionary format
        :return: {(id[int], price[int], discount[int]): {'quantity': float, 'text': string, 'price_per_unit': float} }
        """
        line_dict = {}
        keys = itemgetter('product_id', 'price_unit', 'discount')
        for k, g in groupby(sorted(order_lines, key=keys), key=keys):
            group = list(g)
            unit_price = group[0]['price_subtotal_incl']/group[0]['qty']
            line_dict[k] = {
                'quantity': sum(line['qty'] for line in group),
                'text': group[0]['full_product_name'],
                'price_per_unit': unit_price
            }

        return line_dict

    @api.model
    def retrieve_line_difference(self, ui_orders):
        res = {}
        for order in ui_orders:
            existing_order = None if not order.get('server_id') else self.browse(order['server_id'])
            res[order['uid']] = self._line_differences(existing_order, order)

        return res

    @api.model
    def remove_from_ui(self, server_ids):
        """
        Almost the same as the original method except that we compute the line difference and add it to the response
        """
        if self.env.company.l10n_de_is_germany_and_fiskaly():
            orders = self.search([('id', 'in', server_ids), ('state', '=', 'draft')])
            res = []
            for order in orders:
                differences = self._line_differences(order)
                res.append({'id': order.id, 'differences': differences})
            super().remove_from_ui(server_ids)

            return res
        else:
            return super().remove_from_ui(server_ids)
