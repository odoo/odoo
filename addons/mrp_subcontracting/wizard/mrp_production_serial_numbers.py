# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProductionSerials(models.TransientModel):
    _inherit = 'mrp.production.serials'

    def action_apply(self):
        self.ensure_one()
        sbc_move = self.production_id._get_subcontract_move()
        if not sbc_move:
            return super().action_apply()

        lots = list(filter(lambda serial_number: len(serial_number.strip()) > 0, self.serial_numbers.split('\n'))) if self.serial_numbers else []
        existing_lots = self.env['stock.lot'].search([
            '|', ('company_id', '=', False), ('company_id', '=', self.production_id.company_id.id),
            ('product_id', '=', self.production_id.product_id.id),
            ('name', 'in', lots),
        ])
        existing_lot_names = existing_lots.mapped('name')
        new_lots = []
        sequence = self.production_id.product_id.lot_sequence_id
        for lot_name in sorted(lots):
            if lot_name in existing_lot_names:
                continue
            if sequence and lot_name == sequence.get_next_char(sequence.number_next_actual):
                sequence.sudo().number_next_actual += 1
            new_lots.append({
                'name': lot_name,
                'product_id': self.production_id.product_id.id
            })
        all_lots = existing_lots + self.env['stock.lot'].create(new_lots)
        self.production_id.with_context(mrp_subcontracting=True).write({
            'lot_producing_ids': all_lots[0],
            'product_qty': 1,
        })
        sbc_move.move_line_ids.create([
            {
                'product_id': lot.product_id.id,
                'lot_id': lot.id,
                'move_id': sbc_move.id,
                'quantity': 1,
            } for lot in all_lots[1:]
        ])
        return sbc_move.picking_id.action_show_subcontract_details()
