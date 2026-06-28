from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    repair_order_id = fields.Many2one(related='move_id.repair_order_id')
    repair_service_line_id = fields.Many2one('repair.service.line', check_company=True, copy=False, index='btree_not_null')

    @api.depends('repair_service_line_id.description')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if line.repair_service_line_id and line.repair_service_line_id.description:
                line.name = line.translated_product_name + '\n' + line.repair_service_line_id.description

    def _eligible_for_stock_account(self):
        moves = self._get_stock_moves()
        already_accounted = any(m.repair_id and m.account_move_id for m in moves.filtered(lambda m: m.repair_line_type == 'add'))
        return super()._eligible_for_stock_account() and not already_accounted
