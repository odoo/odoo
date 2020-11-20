# -*- coding: utf-8 -*-

from odoo import models, api


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
            config = self.env['pos.order'].browse(order_id).config_id
        return False if not config else config.is_company_country_germany and config.floor_ids

    @api.model
    def _process_create_from_ui(self, order_ids, ui_order, draft, existing_order):
        """
        The original method only append the id of the orders but in order to be flexible and to not change the
        base code too much, we append a dictionary to add the line differences for each id
        """
        if self._check_config_germany_floor(session_id=ui_order['data']['pos_session_id']):
            differences = self.line_differences(existing_order, ui_order['data'])
            order_id = self._process_order(ui_order, draft, existing_order)
            order_ids.append({'id': order_id, 'differences': differences})
        else:
            super(PosOrder, self)._process_create_from_ui(order_ids, ui_order, draft, existing_order)

    @api.model
    def _create_from_ui_search_read(self, order_ids):
        """
        order_ids should be a list of int but in this module, it can be a list of dict {'id': int, 'differences': list}
        """
        # second condition is to double check just in case
        if not isinstance(order_ids[0], int) and self._check_config_germany_floor(order_id=order_ids[0]['id']):
            ids = list(map(lambda order: order['id'], order_ids))
            res = super(PosOrder, self)._create_from_ui_search_read(ids)

            for json_record in res:
                for order in order_ids:
                    if json_record['id'] == order['id']:
                        if len(order['differences']) > 0:
                            json_record['differences'] = order['differences']
                        break
            return res

        return super(PosOrder, self)._create_from_ui_search_read(order_ids)

    @api.model
    def line_differences(self, existing_order, ui_order):
        """
        :param existing_order: actual PosOrder object
        :param ui_order: json order coming from the front end
        :return: a list of lines difference
        """
        differences = []
        new_line_dict = self._merge_order_lines(list(map(lambda line: line[2], ui_order['lines'])))
        old_lines = existing_order.lines.read(['qty', 'product_id', 'full_product_name', 'price_subtotal_incl'])
        for line in old_lines:
            line['product_id'] = line['product_id'][0]
        old_line_dict = self._merge_order_lines(old_lines)

        for new_line_product_id, new_line in new_line_dict.items():
            if new_line_product_id not in old_line_dict:
                differences.append(new_line)
            elif old_line_dict[new_line_product_id]['quantity'] != new_line['quantity']:
                # we could copy the dict but since it's not going to be used anymore we can just modify it
                new_line['quantity'] -= old_line_dict[new_line_product_id]['quantity']
                differences.append(new_line)

        for old_line_product_id, old_line in old_line_dict.items():
            if old_line_product_id not in new_line_dict:
                old_line['quantity'] = -old_line['quantity']
                differences.append(old_line)

        return differences

    @api.model
    def _merge_order_lines(self, order_lines):
        """
        It is possible to have multiple lines regarding the same product. This method will merge those lines into one
        and create a dictionary with the required information by id
        :param order_lines: The list of lines in a dictionary format
        :return: {int: {'quantity': float, 'text': string, 'price_per_unit': float} }
        """
        line_dict = {}
        for line in order_lines:
            product_id = line['product_id']
            line_qty = line['qty']
            if product_id not in line_dict:
                line_dict[product_id] = {
                    'quantity': line_qty,
                    'text': line['full_product_name'],
                    'price_per_unit': round(line['price_subtotal_incl'] / line_qty, 2)
                }
            else:
                line_dict[product_id]['quantity'] += line_qty
        return line_dict

