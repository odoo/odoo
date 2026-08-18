from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_ids = fields.One2many('stock.move', 'account_move_id', string='Stock Move')
    closing_datetime = fields.Datetime(string='Closing Date')

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _update_average_cost_on_hand(self):
        # the cost is updated at stock move validation when stock is installed
        pass

    def _get_lines_onchange_currency(self):
        # OVERRIDE
        return self.line_ids.filtered(lambda l: l.display_type != 'cogs')

    def copy_data(self, default=None):
        # Don't keep anglo-saxon lines when copying a journal entry.
        vals_list = super().copy_data(default=default)

        if not self.env.context.get('move_reverse_cancel'):
            for vals in vals_list:
                if 'line_ids' in vals:
                    vals['line_ids'] = [line_vals for line_vals in vals['line_ids']
                                             if line_vals[0] != 0 or line_vals[2].get('display_type') != 'cogs']
        return vals_list

    def _post(self, soft=True):
        # OVERRIDE

        # Don't change anything on moves used to cancel another ones.
        if self.env.context.get('move_reverse_cancel'):
            return super()._post(soft)

        # Post entries. (COGS lines are created by the base `_create_cogs_lines`.)
        res = super()._post(soft)

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()

        return res

    def button_draft(self):
        res = super().button_draft()

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()
        return res

    def button_cancel(self):
        # OVERRIDE
        res = super().button_cancel()

        # Unlink the COGS lines generated during the 'post' method.
        # In most cases it shouldn't be necessary since they should be unlinked with 'button_draft'.
        # However, since it can be called in RPC, better be safe.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()

        self.line_ids.cogs_move_ids.filtered(lambda m: m.is_in or m.is_dropship)._set_value()
        return res

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------

    def _update_standard_price(self, reverse=False):
        return

    def _get_invoiced_lot_values(self):
        return []

    def _extract_extra_invoiced_lot_values(self, lot):
        lot.ensure_one()
        # Compute lot properties
        lot_properties = lot.product_id.lot_properties_definition
        # Store the value of each property
        for prop in lot_properties:
            prop['value'] = lot.lot_properties.get(prop['name'])
        return {'lot_properties': lot_properties}
