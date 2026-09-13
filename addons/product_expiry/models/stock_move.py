from re import findall as re_findall

import dateutil.parser as dparser

from odoo import api, fields, models
from odoo.tools import get_lang

from odoo.addons.stock.models.stock_move import FIELD_DATA_IGNORED


class StockMove(models.Model):
    _inherit = "stock.move"

    use_expiration_date = fields.Boolean(
        related="product_id.use_expiration_date",
        string="Use Expiration Date",
    )

    @api.model
    def action_generate_lot_line_vals(
        self, context_data, mode, first_lot, count, lot_text
    ):
        vals_list = super().action_generate_lot_line_vals(
            context_data, mode, first_lot, count, lot_text
        )
        product = self.env["product.product"].browse(
            context_data.get("default_product_id")
        )
        if not product.use_expiration_date:
            for vals in vals_list:
                vals.pop("expiration_date", None)
        picking = self.env["stock.picking"].browse(
            context_data.get("default_picking_id")
        )
        expiration_date = product._get_expiration_date_from(picking.date_planned)
        if expiration_date:
            for vals in vals_list:
                vals["expiration_date"] = vals.get("expiration_date") or expiration_date
        return vals_list

    def _prepare_serial_move_line_commands(
        self, field_data, location_dest_id=False, origin_move_line=None
    ):
        move_lines_commands = super()._prepare_serial_move_line_commands(
            field_data, location_dest_id, origin_move_line
        )
        date = self.product_id._get_expiration_date_from(self.picking_id.date_planned)
        if date:
            for move_line_command in move_lines_commands:
                move_line_vals = move_line_command[2]
                if "expiration_date" not in move_line_vals:
                    move_line_vals["expiration_date"] = date
        return move_lines_commands

    def _str_to_field_data(self, string, options):
        res = super()._str_to_field_data(string, options)
        if not res:
            try:
                parsed_date = dparser.parse(string, **options)
            except ValueError, OverflowError, TypeError:
                return res
            if self and not self.use_expiration_date:
                return FIELD_DATA_IGNORED
            return {"expiration_date": parsed_date}
        return res

    def _get_formatting_options(self, strings):
        options = super()._get_formatting_options(strings)
        separators = "-/ "
        date_regex = f"[^{separators}]+"
        for string in strings:
            date_data = re_findall(date_regex, string)
            if len(date_data) < 2:
                continue
            value_1, value_2 = date_data[:2]
            if re_findall(r"[a-zA-Z]", value_1):
                break
            number_1 = self._parse_date_component(value_1)
            if number_1 is None:
                continue
            if number_1 > 31:
                options["yearfirst"] = True
                break
            number_2 = self._parse_date_component(value_2)
            if number_1 > 12 and (
                re_findall(r"[a-zA-Z]", value_2)
                or (number_2 is not None and number_2 <= 12)
            ):
                options["dayfirst"] = True
                break
            user_lang_format = get_lang(self.env).date_format
            if re_findall(r"^%[mbB]", user_lang_format):
                return options
            elif re_findall(r"^%[djaA]", user_lang_format):
                options["dayfirst"] = True
                break
            elif re_findall(r"^%[yY]", user_lang_format):
                options["yearfirst"] = True
                break
        return options

    @api.model
    def _parse_date_component(self, value):
        try:
            return int(value)
        except ValueError:
            return None

    def _update_reserved_quantity(
        self,
        need,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=True,
    ):
        if self.product_id.use_expiration_date:
            return super(
                StockMove, self.with_context(with_expiration=self.date)
            )._update_reserved_quantity(
                need, location_id, lot_id, package_id, owner_id, strict
            )
        return super()._update_reserved_quantity(
            need, location_id, lot_id, package_id, owner_id, strict
        )

    def _get_available_quantity(
        self,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
        allow_negative=False,
    ):
        if self.product_id.use_expiration_date:
            return super(
                StockMove, self.with_context(with_expiration=self.date)
            )._get_available_quantity(
                location_id, lot_id, package_id, owner_id, strict, allow_negative
            )
        return super()._get_available_quantity(
            location_id, lot_id, package_id, owner_id, strict, allow_negative
        )
