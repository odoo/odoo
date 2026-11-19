# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        result = super()._check_pos_order_lines(pos_config, order, line, fiscal_position_id)
        if result and result[0] in (Command.CREATE, Command.UPDATE) and 'deposit_main_line_id' in line[2]:
            result[2]['deposit_main_line_id'] = line[2]['deposit_main_line_id']
        return result

    def _check_deposit_lines(self):
        for line in self.lines.filtered('deposit_main_line_id'):
            main_line = line.deposit_main_line_id
            if main_line.order_id != self or main_line.product_id.deposit_product_id != line.product_id:
                raise UserError(self.env._("Invalid deposit line"))

        if not self.config_id.module_pos_deposit:
            return
        for main_line in self.lines.filtered('product_id.deposit_product_id'):
            deposit_line = main_line.deposit_line_ids
            if len(deposit_line) != 1 or main_line.product_uom_id.compare(deposit_line.qty, main_line.qty):
                raise UserError(self.env._("Invalid deposit line"))

    def recompute_prices(self):
        self.ensure_one()
        self._check_deposit_lines()
        return super().recompute_prices()
