# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Padding Time

    padding_time = fields.Float(string="Padding", related='company_id.padding_time', readonly=False,
                                help="Amount of time (in hours) during which a product is considered unavailable prior to renting (preparation time).")
    group_rental_stock_picking = fields.Boolean("Rental pickings", implied_group='sale_stock_renting.group_rental_stock_picking')

    @api.onchange('padding_time')
    def _onchange_padding_time(self):
        self.env['ir.property']._set_default("preparation_time", "product.template", self.padding_time)

    def set_values(self):
        rental_group_before = self.env.user.has_group('sale_stock_renting.group_rental_stock_picking')
        super().set_values()
        if rental_group_before and not self.group_rental_stock_picking:
            self.env['stock.warehouse'].update_rental_rules()
        elif not rental_group_before and self.group_rental_stock_picking:
            self.env['res.company'].create_missing_rental_location()
            self.env['stock.warehouse'].update_rental_rules()
