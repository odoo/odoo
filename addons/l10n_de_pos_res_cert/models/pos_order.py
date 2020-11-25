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
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        if self._check_config_germany_floor(session_id=ui_order['pos_session_id']) and 'fiskaly_time_start' not in fields:
            fields['fiskaly_time_start'] = ui_order['creation_date'].replace('T', ' ')[:19]
        return fields

    @api.model
    def _process_create_from_ui(self, order_ids, ui_order, draft, existing_order):
        """
        The original method only append the id of the orders but in order to be flexible and to not change the
        base code too much, we append a dictionary to add the line differences for each id
        """
        # No point in computing the difference if it's to validate the payment of the order
        if draft and self._check_config_germany_floor(session_id=ui_order['data']['pos_session_id']):
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
        if len(order_ids) > 0 and not isinstance(order_ids[0], int) and self._check_config_germany_floor(order_id=order_ids[0]['id']):
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
        old_lines = []
        if existing_order:
            old_lines = existing_order.lines.read(['qty', 'product_id', 'full_product_name', 'price_subtotal_incl',
                                                   'price_unit', 'discount'])
        for line in old_lines:
            line['product_id'] = line['product_id'][0]
        old_line_dict = self._merge_order_lines(old_lines)

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
        for line in order_lines:
            line_qty = line['qty']
            line_key = (line['product_id'], line['price_unit'], line['discount'])
            if line_key not in line_dict:
                unit_price = str(float(line['price_subtotal_incl'] / line_qty))
                if len(unit_price.split('.')[1]) < 2:
                    unit_price += '0'
                line_dict[line_key] = {
                    'quantity': line_qty,
                    'text': line['full_product_name'],
                    'price_per_unit': unit_price
                }
            else:
                line_dict[line_key]['quantity'] += line_qty
        return line_dict

    def _get_fields_for_draft_order(self):
        field_list = super(PosOrder, self)._get_fields_for_draft_order()
        if self.env.company.country_id == self.env.ref('base.de'):
            field_list.append('fiskaly_transaction_uuid')
            field_list.append('fiskaly_time_start')
        return field_list

    @api.model
    def get_table_draft_orders(self, table_id):
        table_orders = super(PosOrder, self).get_table_draft_orders(table_id)
        if self.env.company.country_id == self.env.ref('base.de'):
            for order in table_orders:
                order['fiskaly_uuid'] = order['fiskaly_transaction_uuid']
                order['tss_info'] = {}
                order['tss_info']['time_start'] = order['fiskaly_time_start']

                del order['fiskaly_transaction_uuid']
                del order['fiskaly_time_start']

        return table_orders

    @api.model
    def retrieve_line_difference(self, ui_order):
        existing_order = None
        if ui_order.get('server_id'):
            existing_order = self.env['pos.order'].browse(ui_order['server_id'])
        differences = self.line_differences(existing_order, ui_order)

        return {
            'differences': differences
        }
