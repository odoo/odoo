# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import dateutil.parser as dparser
from re import findall as re_findall

from odoo import api, fields, models
from odoo.tools import get_lang


class StockMove(models.Model):
    _inherit = "stock.move"

    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')

    @api.model
    def action_generate_lot_line_vals(self, context_data, mode, first_lot, count, lot_text):
        vals_list = super().action_generate_lot_line_vals(context_data, mode, first_lot, count, lot_text)
        product = self.env['product.product'].browse(context_data.get('default_product_id'))
        picking = self.env['stock.picking'].browse(context_data.get('default_picking_id'))
        if product.use_expiration_date:
            from_date = picking.scheduled_date or fields.Datetime.today()
            expiration_date = from_date + datetime.timedelta(days=product.expiration_time)
            for vals in vals_list:
                vals['expiration_date'] = vals.get('expiration_date') or expiration_date
        return vals_list

    def _generate_serial_move_line_commands(self, field_data, location_dest_id=False, origin_move_line=None):
        """Override to add a default `expiration_date` into the move lines values."""
        move_lines_commands = super()._generate_serial_move_line_commands(field_data, location_dest_id, origin_move_line)
        if self.product_id.use_expiration_date:
            date = fields.Datetime.today() + datetime.timedelta(days=self.product_id.expiration_time)
            for move_line_command in move_lines_commands:
                move_line_vals = move_line_command[2]
                if 'expiration_date' not in move_line_vals:
                    move_line_vals['expiration_date'] = date
        return move_lines_commands

    def _convert_string_into_field_data(self, string, options):
        res = super()._convert_string_into_field_data(string, options)
        if not res:
            try:
                datetime = dparser.parse(string, **options)
                if self and not self.use_expiration_date:
                    # The datetime was correctly parsed but this move's product doesn't use expiration date.
                    return "ignore"
                return {'expiration_date': datetime}
            except ValueError:
                pass
        return res

    def _get_formating_options(self, strings):
        options = super()._get_formating_options(strings)
        separators = "-/ "
        date_regex = f'[^{separators}]+'
        for string in strings:
            # Searches for a date.
            date_data = re_findall(date_regex, string)
            if len(date_data) < 2:  # Not enough data.
                continue
            value_1, value_2 = date_data[:2]
            if re_findall('[a-zA-Z]', value_1):
                # Assumes the first value is the mounth (written in letters). Don't add any option
                # as mounth as the first date's value is the default behavior for `dateutil.parse`.
                break
            # Try to guess if the first data is the day or the year.
            if int(value_1) > 31:
                options['yearfirst'] = True
                break
            elif int(value_1) > 12 and (re_findall('[a-zA-Z]', value_2) or int(value_2) <= 12):
                options['dayfirst'] = True
                break
            else:  # Too ambiguous, gets the option from the user's lang's date setting.
                user_lang_format = get_lang(self.env).date_format
                if re_findall('^%[mbB]', user_lang_format):  # First parameter is for month.
                    return options
                elif re_findall('^%[djaA]', user_lang_format):  # First parameter is for day.
                    options['dayfirst'] = True
                    break
                elif re_findall('^%[yY]', user_lang_format):  # First parameter is for year.
                    options['yearfirst'] = True
                    break
        return options

    def _update_reserved_quantity(self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        if self.product_id.use_expiration_date:
            return super(StockMove, self.with_context(with_expiration=self.date))._update_reserved_quantity(need, location_id, lot_id, package_id, owner_id, strict)
        return super()._update_reserved_quantity(need, location_id, lot_id, package_id, owner_id, strict)

    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        if self.product_id.use_expiration_date:
            return super(StockMove, self.with_context(with_expiration=self.date))._get_available_quantity(location_id, lot_id, package_id, owner_id, strict, allow_negative)
        return super()._get_available_quantity(location_id, lot_id, package_id, owner_id, strict, allow_negative)
