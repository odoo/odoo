# -*- coding: utf-8 -*-

from odoo import models, fields

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    l10n_mx_edi_weight = fields.Float(compute='_cal_move_line_weight', digits='Stock Weight', compute_sudo=True)

    def _cal_move_line_weight(self):
        moves_lines_with_weight = self.filtered(lambda ml: ml.product_id.weight > 0.00)
        for line in moves_lines_with_weight:
            qty = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id, rounding_method='HALF-UP')
            line.l10n_mx_edi_weight = qty * line.product_id.weight
        (self - moves_lines_with_weight).l10n_mx_edi_weight = 0

    def _get_aggregated_product_quantities(self, **kwargs):
        """Include weight in the dict of aggregated products moved

        returns: dictionary {same_key_as_super: {same_values_as_super, weight: weight}, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        if self.picking_id.l10n_mx_edi_cfdi_state == 'sent':
            for v in aggregated_move_lines.values():
                v['weight'] = v['product_uom']._compute_quantity(v['quantity'], v['product'].uom_id) * v['product'].weight
        return aggregated_move_lines
