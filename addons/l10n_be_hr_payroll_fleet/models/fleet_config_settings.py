# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetConfigSettings(models.TransientModel):
    _name = 'fleet.config.settings'
    _inherit = ['res.config.settings']

    max_unused_cars = fields.Integer(string='Maximum unused cars')

    @api.multi
    def set_default_max_unused_cars(self):
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param("l10n_be_hr_payroll_fleet.max_unused_cars", self.max_unused_cars)

    @api.model
    def get_default_max_unused_cars(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        max_unused_cars = params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=3)
        return dict(max_unused_cars=int(max_unused_cars))
