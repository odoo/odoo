# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        current_location_id = self.location_id
        res = super()._onchange_serial_number()
        if res and not self.lot_name and current_location_id.is_subcontracting_location:
            # we want to avoid auto-updating source location in this case + change the warning message
            self.location_id = current_location_id
            res['warning']['message'] = res['warning']['message'].split("\n\n", 1)[0] + "\n\n" + \
                _("Make sure you validate or adapt the related resupply picking to your subcontractor in order to avoid inconsistencies in your stock.")
        return res

    def write(self, vals):
        for move_line in self:
            if vals.get('lot_id') and move_line.move_id.is_subcontract and move_line.location_id.is_subcontracting_location:
                # Update related subcontracted production to keep consistency between production and reception.
                subcontracted_production = move_line.move_id._get_subcontract_production().filtered(lambda p: p.state not in ('done', 'cancel') and p.lot_producing_id == move_line.lot_id)
                if subcontracted_production:
                    subcontracted_production.lot_producing_id = vals['lot_id']
        return super().write(vals)
