# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetConfigSettings(models.TransientModel):
    _name = 'fleet.config.settings'
    _inherit = ['res.config.settings']

    max_unused_cars = fields.Integer(string='Maximum unused cars')

    def set_values(self):
        super(FleetConfigSettings, self).set_values()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param("l10n_be_hr_payroll_fleet.max_unused_cars", self.max_unused_cars)

    @api.model
    def get_values(self):
        res = super(FleetConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(max_unused_cars=params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=3))
        return res
