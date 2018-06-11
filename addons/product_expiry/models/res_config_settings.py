# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # move this start
    group_expiration_date_on_delivery_slip = fields.Boolean("Display Expiration Dates",
        implied_group='product_expiry.group_expiration_date_on_delivery_slip')
    #move this end

    # move this start
    @api.onchange('group_lot_on_delivery_slip')
    def _onchange_group_lot_on_delivery_slip(self):
        if not self.group_lot_on_delivery_slip:
            self.group_expiration_date_on_delivery_slip = False
    #move this end