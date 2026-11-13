# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        result = super()._check_pos_order_lines(pos_config, order, line, fiscal_position_id)
        if result and result[0] in (Command.CREATE, Command.UPDATE) and 'deposit_main_line_id' in line[2]:
            result[2]['deposit_main_line_id'] = line[2]['deposit_main_line_id']
        return result

    def _check_deposit_lines(self):
        """
        Refuse an order whose deposit lines do not match the products ordered.

        The public self-order payload is the only source of the deposit lines, so a line
        must point to a main line of this order whose product asks for that deposit, and
        every main line must carry exactly one deposit line of the same quantity.
        """
        self.ensure_one()
        for line in self.lines.filtered('deposit_main_line_id'):
            main = line.deposit_main_line_id
            if (
                main.order_id != self
                or not line.product_id.is_deposit
                or main.product_id.deposit_product_id != line.product_id
            ):
                raise UserError(self.env._("Invalid deposit line"))

        if not self.config_id.module_pos_deposit:
            return
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        for main in self.lines.filtered(lambda line: line.product_id.deposit_product_id and not line.deposit_main_line_id):
            if len(main.deposit_line_ids) != 1 or float_compare(main.deposit_line_ids.qty, main.qty, precision_digits=digits):
                raise UserError(self.env._("Invalid deposit line"))

    def recompute_prices(self):
        self.ensure_one()
        self._check_deposit_lines()
        return super().recompute_prices()
