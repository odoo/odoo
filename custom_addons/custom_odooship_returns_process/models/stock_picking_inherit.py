

import logging
from odoo import models,fields, api, _


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    line_number = fields.Integer(string='Return Line Number', index=True)

    @api.model
    def create(self, vals):
        picking_type_id = vals.get('picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id) if picking_type_id else None
        # Use picking_process_type here!
        if (
                picking_type and
                picking_type.picking_process_type == 'returns' and
                vals.get('move_ids_without_package')
        ):
            new_moves = []
            for move in vals['move_ids_without_package']:
                if isinstance(move, (list, tuple)) and move[0] == 0:
                    move_data = dict(move[2])
                    qty = int(float(move_data.get('product_uom_qty', 1)))
                    _logger.info("Splitting move for %s units (move_data: %s)", qty, move_data)
                    for i in range(qty):
                        single_move = move_data.copy()
                        single_move['product_uom_qty'] = 1
                        single_move['name'] = (move_data.get('name') or '') + f" (Return #{i + 1})"
                        new_moves.append((0, 0, single_move))
                else:
                    new_moves.append(move)
            vals['move_ids_without_package'] = new_moves

        return super().create(vals)

    # def write(self, vals):
    #     res = super().write(vals)
    #     if 'move_ids_without_package' in vals or self.picking_type_id.picking_process_type == 'returns':
    #         print("\n\n=======",self.operation_process_type)
    #         for picking in self:
    #             for move in picking.move_ids:
    #                 if move.product_uom_qty > 1:
    #                     qty = int(move.product_uom_qty)
    #                     for i in range(qty):
    #                         new_move = move.copy(default={
    #                             'product_uom_qty': 1,
    #                             'name': (move.name or '') + f" (Return #{i + 1})"
    #                         })
    #                     # move.unlink()
    #     return res


    def action_confirm(self):
        for picking in self:
            # Only for "returns" picking type, don't merge!
            if picking.picking_type_id.picking_process_type == 'returns':
                # Confirm each draft move individually, avoiding any merge/group
                for move in picking.move_ids.filtered(lambda m: m.state == 'draft'):
                    move._action_confirm()
            else:
                # For other types, use Odoo's standard  logic
                super(StockPicking, picking).action_confirm()
        return True

    def action_open_returns_scan_wizard(self):
        self.ensure_one()
        wizard = self.env['returns.scan.wizard'].create({
            'picking_id': self.id,
            'tenant_code_id': self.tenant_code_id.id if self.tenant_code_id else False,
            'site_code_id': self.site_code_id.id if self.site_code_id else False,
            'line_ids': [(0, 0, {
                'product_id': move.product_id.id,
                'name': move.name,
                'qty': move.product_uom_qty,
                'product_grade': move.product_grade,
                'summary': move.summary,
                'line_number': move.line_number,
            }) for move in self.move_ids_without_package],
        })
        return {
            'name': 'Returns Scan Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'returns.scan.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
