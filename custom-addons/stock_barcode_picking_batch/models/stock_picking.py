
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"
    display_batch_button = fields.Boolean(compute='_compute_display_batch_button')

    @api.depends('batch_id')
    def _compute_display_batch_button(self):
        for picking in self:
            picking.display_batch_button = picking.batch_id and picking.batch_id.state == 'in_progress'

    def action_open_batch_picking(self):
        self.ensure_one()
        return self.batch_id.action_client_action()

    def action_unbatch(self):
        self.ensure_one()
        if self.batch_id:
            self.batch_id = False

    def _get_without_quantities_error_message(self):
        if self.env.context.get('barcode_view'):
            return _(
                'You cannot validate a transfer if no quantities are reserved nor done. '
                'You can use the info button on the top right corner of your screen '
                'to remove the transfer in question from the batch.'
            )
        else:
            return super()._get_without_quantities_error_message()
