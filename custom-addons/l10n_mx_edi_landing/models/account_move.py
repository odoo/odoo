# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        # OVERRIDE
        for move in self.filtered(lambda move: move.is_invoice()):
            for line in move.line_ids:
                if line.l10n_mx_edi_customs_number:
                    continue
                stock_moves = line.mapped('sale_line_ids.move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped)
                if not stock_moves:
                    continue
                landed_costs = self.env['stock.landed.cost'].sudo().search([
                    ('picking_ids', 'in', stock_moves.mapped('move_orig_fifo_ids.picking_id').ids),
                    ('l10n_mx_edi_customs_number', '!=', False),
                ])
                if not landed_costs:
                    continue
                line.l10n_mx_edi_customs_number = ','.join(list(set(landed_costs.mapped('l10n_mx_edi_customs_number'))))
        return super()._post(soft)
