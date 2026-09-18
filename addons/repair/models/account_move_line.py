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
                line.name = line.repair_service_line_id.description
            elif line.stock_move_id.repair_id and line.stock_move_id.description_picking_manual:
                line.name = line.stock_move_id.description_picking

    @api.depends('repair_order_id.move_ids.state', 'repair_order_id.move_ids.value')
    def _compute_cogs_move_ids(self):
        # EXTENDS 'stock_account': a repair part leaves stock for the production location, so
        # `sale_stock` skips it when it only keeps the moves going to a customer or a transit.
        super()._compute_cogs_move_ids()
        for aml in self:
            # sudo: the invoice is posted by an accountant, who cannot read a repair order
            moves = aml.sudo().repair_order_id.move_ids.filtered(lambda m:
                m.repair_line_type == 'add' and m.is_valued and m.product_id == aml.product_id
            )
            aml.cogs_move_ids |= moves.with_env(aml.env)

    def _use_inventory_valuation(self):
        moves = self.cogs_move_ids
        already_accounted = any(m.repair_id and m.account_move_id for m in moves.filtered(lambda m: m.repair_line_type == 'add'))
        return super()._use_inventory_valuation() and not already_accounted
