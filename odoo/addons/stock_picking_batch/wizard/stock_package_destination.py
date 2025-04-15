# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChooseDestinationLocation(models.TransientModel):
    _inherit = "stock.package.destination"

    def _compute_move_line_ids(self):
        destination_without_batch = self.env['stock.package.destination']
        for destination in self:
            if not destination.picking_id.batch_id:
                destination_without_batch |= destination
                continue
            destination.move_line_ids = destination.picking_id.batch_id.move_line_ids.filtered(lambda l: l.quantity > 0 and not l.result_package_id)
        super(ChooseDestinationLocation, destination_without_batch)._compute_move_line_ids()

    def action_done(self):
        if self.picking_id.batch_id:
            # set the same location on each move line and pass again in action_put_in_pack
            self.move_line_ids.location_dest_id = self.location_dest_id
            return self.picking_id.batch_id.action_put_in_pack()
        else:
            return super().action_done()
