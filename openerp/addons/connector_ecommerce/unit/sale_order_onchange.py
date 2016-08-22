# -*- coding: utf-8 -*-
##############################################################################
#
#   connector-ecommerce for OpenERP
#   Copyright (C) 2013-TODAY Akretion <http://www.akretion.com>.
#     @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.connector.connector import ConnectorUnit


class OnChangeManager(ConnectorUnit):

    def merge_values(self, record, on_change_result, model=None):
        record.update(self.get_new_values(record, on_change_result,
                                          model=model))

    def get_new_values(self, record, on_change_result, model=None):
        vals = on_change_result.get('value', {})
        new_values = {}
        for fieldname, value in vals.iteritems():
            if fieldname not in record:
                if model:
                    column = self.env[model]._fields[fieldname]
                    if column.type == 'many2many':
                        value = [(6, 0, value)]
                new_values[fieldname] = value
        return new_values


class SaleOrderOnChange(OnChangeManager):
    _model_name = None

    def _get_partner_id_onchange_param(self, order):
        """ Prepare the arguments for calling the partner_id change
        on sales order. You can overwrite this method in your own
        module if they modify the onchange signature

        :param order: a dictionary of the value of your sales order
        :type: dict

        :return: a tuple of args and kwargs for the onchange
        :rtype: tuple
        """
        args = [
            order.get('partner_id'),
        ]
        kwargs = {}
        return args, kwargs

    def _play_order_onchange(self, order):
        """ Play the onchange of the sales order

        :param order: a dictionary of the value of your sales order
        :type: dict

        :return: the value of the sales order updated with the onchange result
        :rtype: dict
        """
        sale_model = self.env['sale.order']
        onchange_specs = sale_model._onchange_spec()

        # we need all fields in the dict even the empty ones
        # otherwise 'onchange()' will not apply changes to them
        all_values = order.copy()
        for field in sale_model._fields:
            if field not in all_values:
                all_values[field] = False

        # we work on a temporary record
        order_record = sale_model.new(all_values)

        new_values = {}

        # Play partner_id onchange
        args, kwargs = self._get_partner_id_onchange_param(order)
        values = order_record.onchange_partner_id(*args, **kwargs)
        new_values.update(self.get_new_values(order, values,
                                              model='sale.order'))
        all_values.update(new_values)

        values = order_record.onchange(all_values,
                                       'payment_method_id',
                                       onchange_specs)
        new_values.update(self.get_new_values(order, values,
                                              model='sale.order'))
        all_values.update(new_values)

        values = order_record.onchange(all_values,
                                       'workflow_process_id',
                                       onchange_specs)
        new_values.update(self.get_new_values(order, values,
                                              model='sale.order'))
        all_values.update(new_values)

        res = {f: v for f, v in all_values.iteritems()
               if f in order or f in new_values}
        return res

    def _get_product_id_onchange_param(self, line, previous_lines, order):
        """ Prepare the arguments for calling the product_id change
        on sales order line. You can overwrite this method in your own
        module if they modify the onchange signature

        :param line: the sales order line to process
        :type: dict
        :param previous_lines: list of dict of the previous lines processed
        :type: list
        :param order: data of the sales order
        :type: dict

        :return: a tuple of args and kwargs for the onchange
        :rtype: tuple
        """
        args = [
            order.get('pricelist_id'),
            line.get('product_id'),
        ]

        # used in sale_markup: this is to ensure the unit price
        # sent by the e-commerce connector is used for markup calculation
        onchange_context = self.env.context.copy()
        if line.get('price_unit'):
            onchange_context.update({'unit_price': line.get('price_unit'),
                                     'force_unit_price': True})

        uos_qty = float(line.get('product_uos_qty', 0))
        if not uos_qty:
            uos_qty = float(line.get('product_uom_qty', 0))

        kwargs = {
            'qty': float(line.get('product_uom_qty', 0)),
            'uom': line.get('product_uom'),
            'qty_uos': uos_qty,
            'uos': line.get('product_uos'),
            'name': line.get('name'),
            'partner_id': order.get('partner_id'),
            'lang': False,
            'update_tax': True,
            'date_order': order.get('date_order'),
            'packaging': line.get('product_packaging'),
            'fiscal_position': order.get('fiscal_position'),
            'flag': False,
            'context': onchange_context,
        }
        return args, kwargs

    def _play_line_onchange(self, line, previous_lines, order):
        """ Play the onchange of the sales order line

        :param line: the sales order line to process
        :type: dict
        :param previous_lines: list of dict of the previous line processed
        :type: list
        :param order: data of the sales order
        :type: dict

        :return: the value of the sales order updated with the onchange result
        :rtype: dict
        """
        line_model = self.env['sale.order.line']
        # Play product_id onchange
        args, kwargs = self._get_product_id_onchange_param(line,
                                                           previous_lines,
                                                           order)
        context = kwargs.pop('context', {})
        values = line_model.with_context(context).product_id_change(*args,
                                                                    **kwargs)
        self.merge_values(line, values, model='sale.order.line')
        return line

    def play(self, order, order_lines):
        """ Play the onchange of the sales order and it's lines

        It expects to receive a recordset containing one sales order.
        It could have been generated with
        ``self.env['sale.order'].new(values)`` or
        ``self.env['sale.order'].create(values)``.

        :param order: data of the sales order
        :type: recordset
        :param order_lines: data of the sales order lines
        :type: recordset

        :return: the sales order updated by the onchanges
        :rtype: recordset
        """
        # play onchange on sales order
        order = self._play_order_onchange(order)

        # play onchange on sales order line
        processed_order_lines = []
        line_lists = [order_lines]
        if 'order_line' in order and order['order_line'] is not order_lines:
            # we have both backend-dependent and oerp-native order
            # lines.
            # oerp-native lines can have been added to map
            # shipping fees with an OpenERP Product
            line_lists.append(order['order_line'])
        for line_list in line_lists:
            for idx, command_line in enumerate(line_list):
                # line_list format:[(0, 0, {...}), (0, 0, {...})]
                if command_line[0] in (0, 1):  # create or update values
                    # keeps command number and ID (or 0)
                    old_line_data = command_line[2]
                    new_line_data = self._play_line_onchange(
                        old_line_data, processed_order_lines, order)
                    new_line = (command_line[0],
                                command_line[1],
                                new_line_data)
                    processed_order_lines.append(new_line)
                    # in place modification of the sales order line in the list
                    line_list[idx] = new_line
        return order
