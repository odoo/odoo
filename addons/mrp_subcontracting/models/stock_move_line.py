# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        current_location_id = self.location_id
        res = super()._onchange_serial_number()
        if res and not self.lot_name and current_location_id.is_subcontract():
            # we want to avoid auto-updating source location in this case + change the warning message
            self.location_id = current_location_id
            res['warning']['message'] = res['warning']['message'].split("\n\n", 1)[0] + "\n\n" + \
                _("Make sure you validate or adapt the related resupply picking to your subcontractor in order to avoid inconsistencies in your stock.")
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('mrp_subcontracting') and ('quantity' in vals or 'lot_id' in vals):
            self.move_id.filtered(lambda m: m.is_subcontract).with_context(no_procurement=True)._sync_subcontracting_productions()
        return res

    def unlink(self):
        moves_to_sync = self.move_id.filtered(lambda m: m.is_subcontract)
        res = super().unlink()
        moves_to_sync._sync_subcontracting_productions()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.move_id.filtered(lambda m: m.is_subcontract)._sync_subcontracting_productions()
        return res
