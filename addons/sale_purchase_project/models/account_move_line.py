# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reinvoiced_so_line_id = fields.Many2one('sale.order.line')

    def _sale_create_reinvoice_sale_line(self):
        result = super()._sale_create_reinvoice_sale_line()
        for move_line in self:
            so_line = result.get(move_line.id)
            if so_line:
                move_line.reinvoiced_so_line_id = so_line
        return result
